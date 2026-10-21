"""A scripted chat model, so an assembled agent can be tested without calling a provider."""

from __future__ import annotations

from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class ScriptedModel(BaseChatModel):
    """Replies from a script (an `Exception` entry is raised), and remembers what the
    harness offered it, the tool_choice of each call, and every message list it was sent."""

    model_name: str = "scripted"
    replies: list[Any]
    offered_tools: list[str] = []
    tool_choices: list[Any] = []
    seen: list[list[Any]] = []

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def _get_ls_params(self, **kwargs: Any) -> dict[str, Any]:
        return {"ls_provider": "scripted", "ls_model_name": self.model_name, "ls_model_type": "chat"}

    def bind_tools(self, tools: Any, **kwargs: Any) -> ScriptedModel:
        self.offered_tools = sorted(t["name"] if isinstance(t, dict) else t.name for t in tools)
        self.tool_choices.append(kwargs.get("tool_choice"))
        return self

    def _generate(
        self, messages: Any, stop: Any = None, run_manager: Any = None, **kwargs: Any
    ) -> ChatResult:
        self.seen.append(list(messages))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return ChatResult(generations=[ChatGeneration(message=reply)])


def call(name: str, call_id: str, **args: Any) -> dict[str, Any]:
    return {"name": name, "args": args, "id": call_id, "type": "tool_call"}


def calls(*tool_calls: dict[str, Any]) -> AIMessage:
    return AIMessage(content="", tool_calls=list(tool_calls))
