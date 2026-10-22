"""The one provider path: Google Gemini, through its OpenAI-compatible chat API.

The harness keeps a provider-neutral messages array; this module is the seam
that translates it to the chat-completions format on every call and
translates the reply back. Configuration comes from the environment or the
git-ignored pair-agent/.env: GEMINI_API_KEY (required) and GEMINI_MODEL
(default gemini-flash-latest, the free-tier Flash model).
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass

import httpx

from pair_agent.tools import Tool

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
DEFAULT_MODEL = "gemini-flash-latest"
# Free-tier models, each with its own daily request quota: when one is spent, switch to another.
FREE_MODELS = ("gemini-flash-latest", "gemini-flash-lite-latest", "gemini-3.5-flash", "gemini-3.1-flash-lite",
               "gemma-4-31b-it")
RETRY_STATUSES = {429, 500, 502, 503, 504}

_STATUS_HINTS = {
    400: "Check GEMINI_API_KEY and GEMINI_MODEL.",
    401: "Gemini rejected the API key. Check GEMINI_API_KEY.",
    403: "This API key may not use the Gemini API. Check the key's project in Google AI Studio.",
    404: "Gemini does not know this model. Check GEMINI_MODEL.",
    429: "Gemini quota or rate limit reached (the free tier has per-minute and per-day limits). Wait and retry.",
    503: "Gemini is overloaded right now. Try again shortly.",
}


class ProviderError(Exception):
    """The model call failed; the message says what to do about it."""


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


def to_chat_messages(messages: list[dict]) -> list[dict]:
    converted = []
    for message in messages:
        role = message["role"]
        if role in ("system", "user"):
            converted.append({"role": role, "content": message["content"]})
        elif role == "assistant":
            entry = {"role": "assistant", "content": message.get("content") or None}
            if message.get("tool_calls"):
                entry["tool_calls"] = []
                for call in message["tool_calls"]:
                    spec = {"id": call["id"], "type": "function",
                            "function": {"name": call["name"], "arguments": json.dumps(call["arguments"])}}
                    if call.get("extra_content"):
                        # Gemini's thought signature must go back with the call it came with.
                        spec["extra_content"] = call["extra_content"]
                    entry["tool_calls"].append(spec)
            converted.append(entry)
        elif role == "tool":
            converted.append({"role": "tool", "tool_call_id": message["tool_call_id"],
                              "content": message["content"] or "(empty result)"})
        else:
            raise ValueError(f"unknown message role: {role}")
    return converted


def to_tool_specs(tools: list[Tool]) -> list[dict]:
    return [
        {"type": "function",
         "function": {"name": t.name, "description": t.description or t.name, "parameters": t.input_schema}}
        for t in tools
    ]


def _arguments(raw: str | dict | None) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError:
        parsed = None
    # Anything unusable reaches the tool registry, which reports it to the model.
    return parsed if isinstance(parsed, dict) else {"_unparseable_arguments": raw}


def from_chat_response(response: dict) -> dict:
    choices = response.get("choices") or []
    if not choices:
        raise ProviderError(f"Gemini returned no choices: {str(response)[:300]}")
    message = choices[0].get("message") or {}
    reply = {"role": "assistant", "content": message.get("content") or ""}
    calls = []
    for raw in message.get("tool_calls") or []:
        call = {"id": raw["id"], "name": raw["function"]["name"],
                "arguments": _arguments(raw["function"].get("arguments"))}
        if raw.get("extra_content"):
            call["extra_content"] = raw["extra_content"]
        calls.append(call)
    if calls:
        reply["tool_calls"] = calls
    if choices[0].get("finish_reason") == "length" and not calls:
        reply["content"] += "\n\n[harness: reply cut off at the output token limit]"
    return reply


def _error_text(response: httpx.Response) -> str:
    """Gemini wraps errors as [{"error": {...}}]; other gateways use {"error": {...}}."""
    try:
        body = response.json()
    except ValueError:
        return response.text[:300]
    if isinstance(body, list) and body:
        body = body[0]
    error = body.get("error", body) if isinstance(body, dict) else body
    return str(error.get("message", error) if isinstance(error, dict) else error)[:300]


class GeminiProvider:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, base_url: str = DEFAULT_BASE_URL,
                 max_tokens: int = 4096, timeout_seconds: float = 120, max_attempts: int = 3,
                 transport: httpx.AsyncBaseTransport | None = None):
        self.model = model
        self.max_tokens = max_tokens
        self.max_attempts = max_attempts
        self.usage = Usage()
        self._client = httpx.AsyncClient(
            base_url=base_url, timeout=timeout_seconds, transport=transport,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    @classmethod
    def from_env(cls, environ: Mapping[str, str | None] = os.environ) -> GeminiProvider:
        api_key = environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ProviderError("GEMINI_API_KEY is not set. Put it in the environment or in "
                                "pair-agent/.env (see .env.example).")
        return cls(api_key, environ.get("GEMINI_MODEL") or DEFAULT_MODEL)

    async def complete(self, messages: list[dict], tools: list[Tool]) -> dict:
        body = {"model": self.model, "messages": to_chat_messages(messages), "max_tokens": self.max_tokens}
        if tools:
            body["tools"] = to_tool_specs(tools)
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = await self._client.post("/chat/completions", json=body)
            except httpx.HTTPError as exc:
                if attempt == self.max_attempts:
                    raise ProviderError(f"Could not reach Gemini: {exc}") from exc
            else:
                if response.status_code == 200:
                    break
                if response.status_code not in RETRY_STATUSES or attempt == self.max_attempts:
                    hint = _STATUS_HINTS.get(response.status_code, "")
                    raise ProviderError(f"Gemini {response.status_code}: {_error_text(response)} {hint}".strip())
            await asyncio.sleep(2 ** attempt)
        payload = response.json()
        usage = payload.get("usage") or {}
        self.usage.input_tokens += usage.get("prompt_tokens", 0)
        self.usage.output_tokens += usage.get("completion_tokens", 0)
        return from_chat_response(payload)

    async def close(self) -> None:
        await self._client.aclose()
