"""The conversation loop and messages array, with a scripted fake provider."""

import pytest

from pair_agent.agent import PairAgent
from pair_agent.tools import Tool, ToolRegistry


class ScriptedProvider:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.seen: list[list[dict]] = []

    async def complete(self, messages, tools):
        self.seen.append([dict(m) for m in messages])
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def registry_with_echo() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(Tool("echo", "Echo text.", {"type": "object"}, lambda text: f"echo: {text}", "harness"))
    return registry


def call(id_, text):
    return {"id": id_, "name": "echo", "arguments": {"text": text}}


async def test_plain_turn_appends_user_and_assistant():
    provider = ScriptedProvider({"role": "assistant", "content": "hi"})
    agent = PairAgent(provider, ToolRegistry(), "SYSTEM")
    assert await agent.send("hello") == "hi"
    assert [m["role"] for m in agent.messages] == ["system", "user", "assistant"]


async def test_earlier_turns_are_sent_back_to_the_model():
    provider = ScriptedProvider({"role": "assistant", "content": "a"}, {"role": "assistant", "content": "b"})
    agent = PairAgent(provider, ToolRegistry(), "SYSTEM")
    await agent.send("first")
    await agent.send("second")
    assert [m.get("content") for m in provider.seen[1]] == ["SYSTEM", "first", "a", "second"]


async def test_tool_calls_run_and_results_are_appended_before_the_final_answer():
    provider = ScriptedProvider(
        {"role": "assistant", "content": "", "tool_calls": [call("1", "x"), call("2", "y")]},
        {"role": "assistant", "content": "done"},
    )
    agent = PairAgent(provider, registry_with_echo(), "SYSTEM")
    assert await agent.send("go") == "done"
    tool_turns = [m for m in agent.messages if m["role"] == "tool"]
    assert [(t["tool_call_id"], t["content"], t["is_error"]) for t in tool_turns] == [
        ("1", "echo: x", False),
        ("2", "echo: y", False),
    ]
    assert provider.seen[1][-1]["role"] == "tool"


async def test_unknown_tool_is_reported_to_the_model_not_raised():
    provider = ScriptedProvider(
        {"role": "assistant", "content": "", "tool_calls": [{"id": "1", "name": "nope", "arguments": {}}]},
        {"role": "assistant", "content": "ok"},
    )
    agent = PairAgent(provider, registry_with_echo(), "SYSTEM")
    await agent.send("go")
    tool_turn = agent.messages[3]
    assert tool_turn["is_error"] and "Unknown tool 'nope'" in tool_turn["content"]


async def test_tool_limit_forces_an_answer_and_leaves_no_dangling_call():
    looping = {"role": "assistant", "content": "", "tool_calls": [call("n", "again")]}
    provider = ScriptedProvider(
        looping, looping,
        {"role": "assistant", "content": "partial answer", "tool_calls": [call("z", "ignored")]},
    )
    agent = PairAgent(provider, registry_with_echo(), "SYSTEM", max_tool_rounds=2)
    assert await agent.send("go") == "partial answer"
    assert "tool_calls" not in agent.messages[-1]
    assert "[harness] Tool limit" in agent.messages[-2]["content"]


async def test_provider_failure_mid_turn_rolls_the_whole_turn_back():
    provider = ScriptedProvider(
        {"role": "assistant", "content": "", "tool_calls": [call("1", "x")]},
        RuntimeError("throttled"),
    )
    agent = PairAgent(provider, registry_with_echo(), "SYSTEM")
    with pytest.raises(RuntimeError):
        await agent.send("go")
    assert agent.messages == [{"role": "system", "content": "SYSTEM"}]


async def test_reset_keeps_only_the_system_prompt():
    agent = PairAgent(ScriptedProvider({"role": "assistant", "content": "x"}), ToolRegistry(), "SYSTEM")
    await agent.send("hi")
    agent.reset()
    assert agent.messages == [{"role": "system", "content": "SYSTEM"}]
