"""The chat agents the hub talks to, behind one small interface.

A chat agent turns one user message into events while it works - token, tool_call,
tool_result - and returns its new conversation state. The state is the agent's own: the
PAIR Agent's messages array, or a Deep Agent's LangChain messages, serialised. Only the
agent's family reads it, to resume a chat or to show it.

A Stop is honoured at the next safe point, never while a tool runs: a tool may be a test
run or a skill script in a worker thread that cancelling could not stop, and a stopped
turn must not leave one going behind the next turn. A stopped turn is rolled back whole.
"""

from __future__ import annotations

import asyncio
import base64
import json
import threading
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml
from agent_kit.harness import Session, text_of
from agent_kit.recording import RunRecorder
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, messages_from_dict, messages_to_dict
from pair_agent.agent import validate_conversation
from pair_agent.provider import FREE_MODELS
from pair_agent.runtime import Runtime

Emit = Callable[[dict], None]
STOP_POLL_SECONDS = 0.2
FILESYSTEM_TOOLS = frozenset({"ls", "read_file", "glob", "grep", "write_file", "edit_file"})


@dataclass(frozen=True)
class Profile:
    key: str
    kind: str  # chat | workflow
    name: str
    module: str
    summary: str


PROFILES = {
    p.key: p
    for p in [
        Profile(
            "pair",
            "chat",
            "PAIR Agent",
            "Module 6",
            "Pair-programs on config-service with the workflow skills and the domain-language MCP.",
        ),
        Profile(
            "doctor",
            "chat",
            "Doctor",
            "Module 7",
            "Diagnoses config-service's health by running its tests and lint. Never edits.",
        ),
        Profile(
            "librarian",
            "chat",
            "Librarian",
            "Module 8",
            "Answers with sources from code, decision notes, the knowledge graph and Git history.",
        ),
        Profile(
            "team",
            "workflow",
            "Codebase Team",
            "Module 9",
            "Doctor, Librarian and Mechanic repair a copy of config-service, with you approving the fix.",
        ),
    ]
}


class TurnStopped(Exception):
    """The user stopped the turn; it was rolled back."""


@dataclass
class TurnResult:
    state: list
    usage: dict[str, int]


def models_for(current: str) -> list[str]:
    return list(dict.fromkeys([current, *FREE_MODELS]))


def read_skills(skills_dir: Path) -> list[dict]:
    """Name and description from each SKILL.md's frontmatter, as the agent's catalog shows them."""
    skills = []
    for path in sorted(skills_dir.glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        meta = yaml.safe_load(text.split("---", 2)[1]) or {}
        skills.append(
            {"name": str(meta.get("name", path.parent.name)), "description": str(meta.get("description", ""))}
        )
    return skills


# -- the PAIR Agent (Module 6): its own loop, async, MCP connections held by the hub ---------


def pair_display(state: list) -> list[dict]:
    """The messages array without Gemini's thought signatures, which only the provider needs."""
    shown = []
    for message in state:
        if message.get("tool_calls"):
            calls = [
                {"id": c["id"], "name": c["name"], "arguments": c["arguments"]} for c in message["tool_calls"]
            ]
            message = {**message, "tool_calls": calls}
        shown.append(message)
    return shown


class PairChat:
    profile = PROFILES["pair"]

    def __init__(self, runtime: Runtime):
        self.runtime = runtime
        self.models = models_for(runtime.provider.model)

    @property
    def model(self) -> str:
        return self.runtime.provider.model

    def set_model(self, model: str) -> None:
        self.runtime.provider.model = model  # from the next model call on

    def describe(self) -> dict:
        return {
            "system_prompt": self.runtime.system_prompt,
            "max_rounds": self.runtime.max_tool_rounds,
            "skills": [{"name": s["name"], "description": s["description"]} for s in self.runtime.skills],
            "tools": [
                {"name": t.name, "source": t.source, "description": t.description}
                for t in self.runtime.registry.all()
            ],
        }

    @staticmethod
    def validate(state: object) -> list:
        return validate_conversation(state)

    display = staticmethod(pair_display)

    def export(self, state: list) -> list:
        """The terminal's /save format, which its /load reads."""
        return [{"role": "system", "content": self.runtime.system_prompt}, *state]

    async def run_turn(
        self, session_id: str, state: list, text: str, emit: Emit, stop: threading.Event
    ) -> TurnResult:
        in_tool = False

        def on_event(kind: str, data: dict) -> None:
            nonlocal in_tool
            if kind == "tool_call":
                if stop.is_set():
                    raise TurnStopped
                in_tool = True
                emit(
                    {
                        "type": "tool_call",
                        "id": data["id"],
                        "name": data["name"],
                        "arguments": data["arguments"],
                    }
                )
            elif kind == "tool_result":
                in_tool = False
                emit(
                    {
                        "type": "tool_result",
                        "id": data["id"],
                        "name": data["name"],
                        "is_error": data["is_error"],
                        "chars": data["chars"],
                    }
                )
                if stop.is_set():
                    raise TurnStopped

        agent = self.runtime.new_agent(on_event)
        agent.messages.extend(state)
        usage = self.runtime.provider.usage
        before = usage.input_tokens, usage.output_tokens
        turn = asyncio.ensure_future(agent.send(text))
        try:
            while not turn.done():
                await asyncio.wait({turn}, timeout=STOP_POLL_SECONDS)
                if stop.is_set() and not in_tool and not turn.done():
                    turn.cancel()  # mid model call: nothing is running that cancelling leaves behind
        finally:
            if not turn.done():  # the hub itself is shutting down
                turn.cancel()
        if turn.cancelled():
            raise TurnStopped
        await turn  # raises the turn's error; the agent has rolled it back
        return TurnResult(
            agent.messages[1:],
            {
                "input_tokens": usage.input_tokens - before[0],
                "output_tokens": usage.output_tokens - before[1],
            },
        )


# -- Deep Agents specialists (Modules 7 and 8): agent-kit Sessions, run in a worker thread ----


def _jsonable(value: Any) -> str:
    if isinstance(value, bytes):  # a thought signature; Gemini's client reads base64 back
        return base64.b64encode(value).decode("ascii")
    raise TypeError(f"{type(value).__name__} is not JSON serialisable")


def dump_messages(messages: list) -> list[dict]:
    return json.loads(json.dumps(messages_to_dict(messages), default=_jsonable))


def deep_display(state: list) -> list[dict]:
    shown: list[dict] = []
    for message in messages_from_dict(state):
        if isinstance(message, HumanMessage):
            shown.append({"role": "user", "content": text_of(message.content)})
        elif isinstance(message, AIMessage):
            entry: dict = {"role": "assistant", "content": text_of(message.content)}
            if message.tool_calls:
                entry["tool_calls"] = [
                    {"id": c["id"], "name": c["name"], "arguments": c["args"]} for c in message.tool_calls
                ]
            shown.append(entry)
        elif isinstance(message, ToolMessage):
            content = text_of(message.content)
            shown.append(
                {
                    "role": "tool",
                    "tool_call_id": message.tool_call_id,
                    "name": message.name or "tool",
                    "content": content,
                    "is_error": message.status == "error" or content.startswith("Error"),
                }
            )
    return shown


def _ui_event(event: dict) -> dict:
    if event["type"] == "token":
        return event
    if event["type"] == "tool_call":
        return {"type": "tool_call", "id": event["id"], "name": event["name"], "arguments": event["args"]}
    return {
        "type": "tool_result",
        "id": event["id"],
        "name": event["name"],
        "is_error": event["status"] == "error",
        "chars": event["chars"],
    }


class DeepChat:
    """A Doctor or a Librarian. Each chat keeps its own agent-kit Session (and so its own
    recording, named after the chat) for as long as the hub runs."""

    def __init__(
        self,
        key: str,
        build: Callable[[str, RunRecorder], Session],
        model: str,
        runs_dir: Path,
        system_prompt: str,
        excluded_tools: frozenset[str],
        skills_dir: Path,
    ):
        self.profile = PROFILES[key]
        self.build = build
        self.model = model
        self.models = models_for(model)
        self.runs_dir = runs_dir
        self._sessions: dict[str, Session] = {}
        probe = build(model, RunRecorder(runs_dir, "hub-describe"))
        offered = probe.graph.nodes["tools"].bound.tools_by_name
        self._describe = {
            "system_prompt": system_prompt,
            "max_rounds": 12,
            "skills": read_skills(skills_dir),
            "tools": [
                {
                    "name": name,
                    "source": "filesystem" if name in FILESYSTEM_TOOLS else key,
                    "description": tool.description,
                }
                for name, tool in offered.items()
                if name not in excluded_tools
            ],
        }

    def set_model(self, model: str) -> None:
        self.model = model
        self._sessions.clear()  # rebuilt on the new model; each chat's state is in the store

    def describe(self) -> dict:
        return self._describe

    @staticmethod
    def validate(state: object) -> list:
        if not isinstance(state, list):
            raise ValueError("expected a list of serialised messages")
        messages_from_dict(state)
        return state

    display = staticmethod(deep_display)

    @staticmethod
    def export(state: list) -> list:
        return state

    async def run_turn(
        self, session_id: str, state: list, text: str, emit: Emit, stop: threading.Event
    ) -> TurnResult:
        if session_id not in self._sessions:
            self._sessions[session_id] = self.build(self.model, RunRecorder(self.runs_dir, session_id))
        session = self._sessions[session_id]
        session.messages = messages_from_dict(state)
        loop = asyncio.get_running_loop()

        def work() -> bool:
            """Pull the turn one event at a time: the graph runs a tool, or calls the model,
            only when asked for the next event. After a Stop, the tools already called finish
            and report, and the turn ends before the next model call."""
            events = session.stream(text)
            pending: set[str] = set()
            try:
                for event in events:
                    if event["type"] == "final":
                        return True  # the turn completed; a late Stop is too late to undo it
                    if event["type"] == "tool_call":
                        if stop.is_set():
                            return False  # called but not started
                        pending.add(event["id"])
                    elif event["type"] == "tool_result":
                        pending.discard(event["id"])
                    elif stop.is_set():
                        return False
                    loop.call_soon_threadsafe(emit, _ui_event(event))
                    if stop.is_set() and not pending:
                        return False
                return True
            finally:
                events.close()  # on a Stop, records the turn as failed and keeps the old messages

        if not await asyncio.to_thread(work):
            raise TurnStopped
        new = session.messages[len(state) :]
        usage = {"input_tokens": 0, "output_tokens": 0}
        for message in new:
            counted = getattr(message, "usage_metadata", None) or {}
            for key in usage:
                usage[key] += counted.get(key, 0)
        return TurnResult(dump_messages(session.messages), usage)


def doctor() -> DeepChat:
    from doctor_agent.agent import EXCLUDED_TOOLS, DoctorAgent
    from doctor_agent.config import DoctorConfig
    from doctor_agent.prompts import SYSTEM_PROMPT

    config = DoctorConfig.load()
    return DeepChat(
        "doctor",
        lambda model, recorder: DoctorAgent(replace(config, model=model), recorder),
        config.model,
        config.runs_dir,
        SYSTEM_PROMPT,
        EXCLUDED_TOOLS,
        config.skills_dir,
    )


def librarian() -> DeepChat:
    from librarian_agent.agent import EXCLUDED_TOOLS, LibrarianAgent, build_embedder
    from librarian_agent.config import LibrarianConfig
    from librarian_agent.prompts import SYSTEM_PROMPT

    config = LibrarianConfig.load()
    config.require_key()
    embedder = build_embedder(config)
    return DeepChat(
        "librarian",
        lambda model, recorder: LibrarianAgent(replace(config, model=model), recorder, embedder),
        config.model,
        config.memory_dir,
        SYSTEM_PROMPT,
        EXCLUDED_TOOLS,
        config.skills_dir,
    )


DISPLAY = {"pair": pair_display, "doctor": deep_display, "librarian": deep_display}
