"""Deep Agents plumbing every specialist shares: the Gemini model, the retry policy,
the trimmed tool surface, and a `Session` that runs and records conversation turns.

What a specialist adds on top - and what makes it a Doctor, a Librarian or a
Mechanic - is its system prompt, its own tools, its skills and its mounts.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Awaitable, Callable, Iterator, Mapping, Sequence
from typing import Any

from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend
from deepagents.backends.protocol import BackendProtocol
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse, ModelRetryMiddleware
from langchain.agents.middleware.types import ExtendedModelResponse
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.chat_models import GoogleAPIError, GoogleRateLimitError
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

from agent_kit.recording import RunRecorder, compact

RECORDED_RESULT_CHARS = 4000
STREAM_MODES = ["messages", "updates", "values"]


def gemini(model: str, api_key: str) -> BaseChatModel:
    return ChatGoogleGenerativeAI(model=model, api_key=api_key)


def transient(exc: Exception) -> bool:
    """Worth retrying: a 5xx overload or a per-minute 429. A spent per-day free-tier
    quota resets at midnight Pacific, so waiting it out in a retry loop is pointless."""
    if isinstance(exc, GoogleRateLimitError):
        return "PerDay" not in str(exc)
    return isinstance(exc, GoogleAPIError)


def model_retry() -> ModelRetryMiddleware:
    # The model client's own retries do not cover streamed calls, which is how Deep
    # Agents calls it; this wraps every model call in the loop.
    return ModelRetryMiddleware(
        max_retries=4, retry_on=transient, on_failure="error", initial_delay=5.0, max_delay=60.0
    )


class ToolSurface(AgentMiddleware):
    """Removes tools from what this agent's model is offered, and refuses calls to them.

    Per agent, on purpose: Deep Agents' harness profiles live in a process-wide registry
    that unions exclusions, so a Doctor and a Mechanic on the same model in one process
    would share the Doctor's narrower tool set.
    """

    def __init__(self, excluded: frozenset[str]):
        super().__init__()
        self.excluded = excluded

    def _offer(self, request: ModelRequest) -> ModelRequest:
        names = (t["name"] if isinstance(t, dict) else t.name for t in request.tools)
        return request.override(
            tools=[t for t, n in zip(request.tools, names, strict=True) if n not in self.excluded]
        )

    def _refuse(self, request: ToolCallRequest) -> ToolMessage | None:
        name = request.tool_call["name"]
        if name not in self.excluded:
            return None
        return ToolMessage(
            content=f"Error: {name} is not available to this agent.",
            tool_call_id=request.tool_call["id"] or "",
            name=name,
            status="error",
        )

    def wrap_model_call(self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]) -> Any:
        return handler(self._offer(request))

    async def awrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Awaitable[ModelResponse]]
    ) -> Any:
        return await handler(self._offer(request))

    def wrap_tool_call(
        self, request: ToolCallRequest, handler: Callable[[ToolCallRequest], ToolMessage | Command]
    ) -> ToolMessage | Command:
        return self._refuse(request) or handler(request)

    async def awrap_tool_call(
        self, request: ToolCallRequest, handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]]
    ) -> ToolMessage | Command:
        return self._refuse(request) or await handler(request)


FINAL_ROUND = (
    "\n\nThis is your last step in this turn: tools are off. Answer now with the evidence you "
    "already have, and say plainly what you did not get to check."
)
STOPPED = (
    "I reached my step limit for this turn before finishing. Ask me to continue, or narrow the question."
)


def _answer_only(message: Any) -> Any:
    if not isinstance(message, AIMessage) or not message.tool_calls:
        return message
    return AIMessage(content=text_of(message.content).strip() or STOPPED, id=message.id)


def _without_tool_calls(result: Any) -> Any:
    """The final round's reply with any tool calls dropped, whatever wrapper carries it."""
    if isinstance(result, ExtendedModelResponse):
        result.model_response = _without_tool_calls(result.model_response)
    elif isinstance(result, ModelResponse):
        result.result = [_answer_only(m) for m in result.result]
    else:
        result = _answer_only(result)
    return result


class RoundBudget(AgentMiddleware):
    """At most `rounds` model calls per turn; the last one is told to answer with what it has,
    and its reply is an answer even if the model tries to call a tool.

    Each tool round is one request, and the free tier allows about 20 a day per model: an
    agent that keeps reading until the quota runs out answers nothing. Module 6's
    hand-rolled loop had this rule; a framework loop does not, unless it is added.

    Asking is not enough: Gemini ignores `tool_choice="none"`, and still calls a tool when
    no tools are declared but the history holds tool calls (both measured). So the
    request asks, and the response is enforced.
    """

    def __init__(self, rounds: int):
        super().__init__()
        if rounds < 1:
            raise ValueError("A turn needs at least one model call.")
        self.rounds = rounds

    def _final(self, request: ModelRequest) -> bool:
        since_user = 0
        for message in reversed(request.messages):
            if isinstance(message, HumanMessage):
                break
            since_user += isinstance(message, AIMessage)
        return since_user >= self.rounds - 1

    @staticmethod
    def _ask_for_an_answer(request: ModelRequest) -> ModelRequest:
        system = request.system_message
        content = system.content if system else ""
        content = (
            [*content, {"type": "text", "text": FINAL_ROUND}]
            if isinstance(content, list)
            else content + FINAL_ROUND
        )
        return request.override(tool_choice="none", system_message=SystemMessage(content=content))

    def wrap_model_call(self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]) -> Any:
        if not self._final(request):
            return handler(request)
        return _without_tool_calls(handler(self._ask_for_an_answer(request)))

    async def awrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Awaitable[ModelResponse]]
    ) -> Any:
        if not self._final(request):
            return await handler(request)
        return _without_tool_calls(await handler(self._ask_for_an_answer(request)))


def assemble(
    model: BaseChatModel,
    *,
    system_prompt: str,
    tools: Sequence[BaseTool],
    routes: Mapping[str, BackendProtocol],
    excluded_tools: frozenset[str],
    permissions: Sequence[FilesystemPermission],
    rounds: int = 12,
) -> CompiledStateGraph:
    """A Deep Agent with skills under `/skills/`, the given mounts, and nothing else, that
    answers within `rounds` model calls per turn.

    Paths outside the mounts land in Deep Agents' in-memory state backend, not on disk.
    """
    return create_deep_agent(
        model=model,
        tools=list(tools),
        system_prompt=system_prompt,
        middleware=[ToolSurface(excluded_tools), RoundBudget(rounds), model_retry()],
        skills=["/skills/"],
        backend=CompositeBackend(default=StateBackend(), routes=dict(routes)),
        permissions=list(permissions),
        checkpointer=False,
    )


def text_of(content: Any) -> str:
    """Message content as plain text: Gemini returns a list of typed blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block if isinstance(block, str) else str(block.get("text", ""))
            for block in content
            if isinstance(block, str) or block.get("type") == "text"
        )
    return ""


def skill_read(call: dict[str, Any]) -> str | None:
    path = str(call["args"].get("file_path", "")) if call["name"] == "read_file" else ""
    if path.startswith("/skills/") and path.endswith("/SKILL.md"):
        return path.removeprefix("/skills/").removesuffix("/SKILL.md")
    return None


def result_fields(content: str) -> dict[str, Any]:
    """`passed`, `exit_code` and `error` from a tool's JSON result, for the artifacts."""
    try:
        parsed = json.loads(content)
    except ValueError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {key: parsed[key] for key in ("passed", "exit_code", "error") if key in parsed}


class Session:
    """A compiled agent plus the conversation so far, recorded turn by turn."""

    def __init__(self, graph: CompiledStateGraph, recorder: RunRecorder):
        self.graph = graph
        self.recorder = recorder
        self.messages: list[AnyMessage] = []

    def ask(self, user_message: str) -> str:
        return next(e["text"] for e in self.stream(user_message) if e["type"] == "final")

    def stream(self, user_message: str) -> Iterator[dict[str, Any]]:
        """Run one turn, yielding token / tool_call / tool_result events, then one final event.

        The conversation only advances if the turn completes: on an error the
        messages are left as they were, so the session stays usable.
        """
        turn = Turn(self.recorder)
        self.recorder.conversation("user_message", trace_id=turn.trace_id, content=user_message)
        state = [*self.messages, HumanMessage(user_message)]
        try:
            for mode, chunk in self.graph.stream({"messages": state}, stream_mode=STREAM_MODES):
                if mode == "values":
                    state = chunk["messages"]
                elif mode == "messages":
                    message, metadata = chunk
                    token = text_of(message.content) if metadata.get("langgraph_node") == "model" else ""
                    if token:
                        yield {"type": "token", "text": token}
                else:
                    for message in _updated_messages(chunk):
                        if isinstance(message, AIMessage):
                            yield from turn.model_replied(message)
                        elif isinstance(message, ToolMessage):
                            yield turn.tool_returned(message)
        except BaseException as exc:  # Ctrl+C too: the turn is still recorded as failed
            turn.failed(exc)
            raise
        self.messages = state
        yield {"type": "final", "text": turn.finished()}


class Turn:
    """One conversation turn as recorded events: model calls, tool calls, the final reply."""

    def __init__(self, recorder: RunRecorder):
        self.recorder = recorder
        self.trace_id = uuid.uuid4().hex[:12]
        self.started = self.mark = time.perf_counter()
        self.pending: dict[str, tuple[str, float]] = {}
        self.final_text = ""

    def _lap(self) -> int:
        """Milliseconds since the last model reply or tool result, and restart the clock."""
        now = time.perf_counter()
        elapsed, self.mark = round((now - self.mark) * 1000), now
        return elapsed

    def model_replied(self, message: AIMessage) -> Iterator[dict[str, Any]]:
        model_ms = self._lap()
        calls = message.tool_calls
        self.recorder.trace(
            "model_call", self.trace_id, duration_ms=model_ms, tool_calls=[c["name"] for c in calls]
        )
        if not calls:
            self.final_text = text_of(message.content)
            self.recorder.trace("final_response", self.trace_id, duration_ms=model_ms, status="ok")
        for call in calls:
            self.pending[call["id"]] = (call["name"], self.mark)
            self.recorder.conversation(
                "tool_call",
                trace_id=self.trace_id,
                tool=call["name"],
                call_id=call["id"],
                arguments=call["args"],
            )
            if skill := skill_read(call):
                self.recorder.conversation("skill_read", trace_id=self.trace_id, skill=skill)
                self.recorder.trace("skill_load", self.trace_id, skill=skill)
            yield {"type": "tool_call", "name": call["name"], "args": call["args"]}

    def tool_returned(self, message: ToolMessage) -> dict[str, Any]:
        name, called_at = self.pending.pop(message.tool_call_id, (message.name or "tool", self.mark))
        self._lap()
        content = text_of(message.content)
        fields = result_fields(content)
        failed = message.status == "error" or content.startswith("Error") or bool(fields.get("error"))
        status = "error" if failed else "ok"
        self.recorder.conversation(
            "tool_result",
            trace_id=self.trace_id,
            tool=name,
            call_id=message.tool_call_id,
            status=status,
            **fields,
            content=compact(content, RECORDED_RESULT_CHARS),
        )
        self.recorder.trace(
            "tool_call",
            self.trace_id,
            tool=name,
            call_id=message.tool_call_id,
            duration_ms=round((self.mark - called_at) * 1000),
            status=status,
        )
        return {"type": "tool_result", "name": name, "status": status, **fields}

    def failed(self, exc: BaseException) -> None:
        self.recorder.conversation("error", trace_id=self.trace_id, error=f"{type(exc).__name__}: {exc}")
        self.recorder.trace("conversation_turn", self.trace_id, duration_ms=self._total_ms(), status="error")

    def finished(self) -> str:
        text = self.final_text or "(The model returned no text.)"
        self.recorder.conversation("assistant_message", trace_id=self.trace_id, content=text)
        self.recorder.trace("conversation_turn", self.trace_id, duration_ms=self._total_ms(), status="ok")
        return text

    def _total_ms(self) -> int:
        return round((time.perf_counter() - self.started) * 1000)


def _updated_messages(chunk: dict[str, Any]) -> list[Any]:
    """This turn's new messages in a LangGraph `updates` chunk: {node: {"messages": [...]}}.

    Only the model and tools nodes add messages. Middleware nodes can re-emit the whole
    history (Deep Agents patches a dangling tool call that way), which is not news.
    """
    found: list[Any] = []
    for node, update in chunk.items():
        if node not in ("model", "tools"):
            continue
        messages = update.get("messages") if isinstance(update, dict) else None
        if isinstance(messages, list):
            found.extend(messages)
    return found
