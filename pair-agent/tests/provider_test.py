"""Translation between the harness's messages array and Gemini's chat API, and
error handling, against a mocked HTTP transport (no network, no cost)."""

import json

import httpx
import pytest

from pair_agent.provider import (
    GeminiProvider,
    ProviderError,
    from_chat_response,
    to_chat_messages,
    to_tool_specs,
)
from pair_agent.tools import Tool

SIGNATURE = {"google": {"thought_signature": "sig-123"}}


def test_messages_translate_and_thought_signatures_go_back_with_their_call():
    converted = to_chat_messages([
        {"role": "system", "content": "S"},
        {"role": "user", "content": "q"},
        {"role": "assistant", "content": "", "tool_calls": [
            {"id": "a", "name": "t", "arguments": {"x": 1}, "extra_content": SIGNATURE},
        ]},
        {"role": "tool", "tool_call_id": "a", "name": "t", "content": "", "is_error": False},
        {"role": "assistant", "content": "answer"},
    ])
    assert [m["role"] for m in converted] == ["system", "user", "assistant", "tool", "assistant"]
    call = converted[2]["tool_calls"][0]
    assert call["function"] == {"name": "t", "arguments": '{"x": 1}'}
    assert call["extra_content"] == SIGNATURE
    assert converted[2]["content"] is None
    assert converted[3] == {"role": "tool", "tool_call_id": "a", "content": "(empty result)"}


def test_reply_with_tool_calls_is_parsed_and_keeps_the_signature():
    reply = from_chat_response({"choices": [{"finish_reason": "tool_calls", "message": {
        "content": None,
        "tool_calls": [{"id": "c1", "type": "function", "extra_content": SIGNATURE,
                        "function": {"name": "lookup", "arguments": '{"term": "x"}'}}],
    }}]})
    assert reply == {"role": "assistant", "content": "", "tool_calls": [
        {"id": "c1", "name": "lookup", "arguments": {"term": "x"}, "extra_content": SIGNATURE},
    ]}


def test_unparseable_arguments_reach_the_registry_instead_of_crashing():
    reply = from_chat_response({"choices": [{"message": {"tool_calls": [
        {"id": "c1", "type": "function", "function": {"name": "t", "arguments": "{oops"}},
    ]}}]})
    assert reply["tool_calls"][0]["arguments"] == {"_unparseable_arguments": "{oops"}


def test_length_cut_off_is_flagged():
    reply = from_chat_response({"choices": [{"finish_reason": "length", "message": {"content": "partial"}}]})
    assert reply["content"].startswith("partial") and "cut off" in reply["content"]


def test_tool_specs_use_name_as_fallback_description():
    tool = Tool("t", "", {"type": "object"}, lambda: None, "harness")
    assert to_tool_specs([tool]) == [
        {"type": "function", "function": {"name": "t", "description": "t", "parameters": {"type": "object"}}},
    ]


def provider_answering(*responses: httpx.Response) -> tuple[GeminiProvider, list[dict]]:
    sent: list[dict] = []
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append({"auth": request.headers["Authorization"], "body": json.loads(request.content)})
        return queue.pop(0)

    provider = GeminiProvider("test-key", transport=httpx.MockTransport(handler))
    return provider, sent


OK = {"choices": [{"finish_reason": "stop", "message": {"content": "hi"}}],
      "usage": {"prompt_tokens": 7, "completion_tokens": 2}}


async def test_request_shape_and_usage():
    provider, sent = provider_answering(httpx.Response(200, json=OK))
    tool = Tool("t", "d", {"type": "object"}, lambda: None, "harness")
    reply = await provider.complete([{"role": "user", "content": "q"}], [tool])
    assert reply == {"role": "assistant", "content": "hi"}
    assert sent[0]["auth"] == "Bearer test-key"
    assert sent[0]["body"]["model"] == "gemini-flash-latest"
    assert sent[0]["body"]["tools"][0]["function"]["name"] == "t"
    assert (provider.usage.input_tokens, provider.usage.output_tokens) == (7, 2)


async def test_overload_is_retried(monkeypatch):
    monkeypatch.setattr("pair_agent.provider.asyncio.sleep", _no_sleep)
    busy = httpx.Response(503, json=[{"error": {"code": 503, "message": "high demand"}}])
    provider, sent = provider_answering(busy, httpx.Response(200, json=OK))
    assert (await provider.complete([{"role": "user", "content": "q"}], []))["content"] == "hi"
    assert len(sent) == 2


async def test_bad_key_fails_at_once_with_geminis_message_and_a_hint():
    bad = httpx.Response(400, json=[{"error": {"code": 400, "message": "API key not valid."}}])
    provider, sent = provider_answering(bad)
    with pytest.raises(ProviderError, match="Gemini 400: API key not valid. Check GEMINI_API_KEY"):
        await provider.complete([{"role": "user", "content": "q"}], [])
    assert len(sent) == 1


def test_missing_key_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ProviderError, match="GEMINI_API_KEY is not set"):
        GeminiProvider.from_env()


async def _no_sleep(seconds):
    return None
