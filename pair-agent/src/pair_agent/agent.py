"""The harness core: a messages array and the loop that drives it."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from pair_agent.tools import Tool, ToolRegistry


def validate_conversation(loaded: object) -> list[dict]:
    """A saved conversation, minus its system prompt, checked so that a bad file cannot
    leave the array in a state the provider will reject on every later turn."""
    if not isinstance(loaded, list) or not all(isinstance(m, dict) for m in loaded):
        raise ValueError("expected a JSON list of message objects")
    messages = [m for m in loaded if m.get("role") != "system"]
    pending: set[str] = set()
    for message in messages:
        role = message.get("role")
        if role not in ("user", "assistant", "tool") or not isinstance(message.get("content", ""), str):
            raise ValueError(f"unexpected message: {str(message)[:80]}")
        if role == "tool":
            pending.discard(message.get("tool_call_id"))
            continue
        if pending:
            raise ValueError(f"tool call(s) without results: {', '.join(sorted(pending))}")
        pending = {call["id"] for call in message.get("tool_calls", [])}
    if pending:
        raise ValueError(f"tool call(s) without results: {', '.join(sorted(pending))}")
    return messages


class Provider(Protocol):
    async def complete(self, messages: list[dict], tools: list[Tool]) -> dict: ...


class PairAgent:
    def __init__(
        self,
        provider: Provider,
        registry: ToolRegistry,
        system_prompt: str,
        max_tool_rounds: int = 12,
        on_event: Callable[[str, dict], None] | None = None,
    ):
        self.provider = provider
        self.registry = registry
        self.max_tool_rounds = max_tool_rounds
        self.on_event = on_event or (lambda kind, data: None)
        self.messages: list[dict] = [{"role": "system", "content": system_prompt}]

    def reset(self) -> None:
        self.messages = self.messages[:1]

    async def send(self, text: str) -> str:
        """One user turn. If anything fails, or the turn is cancelled, mid-turn, the turn is
        rolled back whole so the array never holds a tool call without its result."""
        turn_start = len(self.messages)
        try:
            return await self._turn(text)
        except BaseException:
            del self.messages[turn_start:]
            raise

    async def _turn(self, text: str) -> str:
        """Call the model, run any tools it asks for, repeat until it answers."""
        self.messages.append({"role": "user", "content": text})
        for _ in range(self.max_tool_rounds):
            reply = await self.provider.complete(self.messages, self.registry.all())
            self.messages.append(reply)
            calls = reply.get("tool_calls", [])
            if not calls:
                return reply["content"]
            for call in calls:
                self.on_event("tool_call", call)
                outcome = await self.registry.execute(call["name"], call["arguments"])
                self.on_event("tool_result", {"id": call["id"], "name": call["name"],
                                              "is_error": outcome.is_error, "chars": len(outcome.content)})
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "name": call["name"],
                    "content": outcome.content,
                    "is_error": outcome.is_error,
                })
        # The model still wants tools; ask it to answer with what it has rather than loop forever.
        self.messages.append({
            "role": "user",
            "content": f"[harness] Tool limit of {self.max_tool_rounds} rounds reached. "
                       "Answer now with what you have, and say what you could not check.",
        })
        # Tools stay declared so the transcript's earlier calls still make sense, but any
        # further calls are dropped so the array never holds a call with no result.
        reply = await self.provider.complete(self.messages, self.registry.all())
        reply.pop("tool_calls", None)
        reply["content"] = reply["content"] or "(stopped at the tool limit without an answer)"
        self.messages.append(reply)
        return reply["content"]
