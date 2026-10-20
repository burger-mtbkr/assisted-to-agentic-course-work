"""Text to unit vectors. Two interchangeable embedders behind one small interface.

`GeminiEmbedder` is the real one: meaning-level recall ("validate before saving"
finds "validated at write time"). `HashingEmbedder` is deterministic and offline:
shared words and word stems only. Tests use it so they never call a provider.
"""

from __future__ import annotations

import hashlib
import math
import re
import time
from collections.abc import Callable, Sequence
from typing import Protocol

Vector = list[float]
# The free tier counts every text in a batch as one request (100 a minute) and also caps
# tokens per minute. Batches stay under both - BATCH_SIZE texts and about BATCH_TOKENS
# tokens (estimated at 3 characters each, cautious for code) - one batch per PACE_SECONDS.
BATCH_SIZE = 90
BATCH_TOKENS = 15_000
PACE_SECONDS = 61.0
MAX_RATE_LIMIT_WAITS = 5
STOPWORDS = frozenset(
    "a an and are as at be by do does for from how i in is it of on or that the this to was we what when "
    "where which who why with".split()
)


class Embedder(Protocol):
    name: str  # recorded in the index: vectors from different embedders do not mix

    def embed_documents(self, texts: Sequence[str]) -> list[Vector]: ...

    def embed_query(self, text: str) -> Vector: ...


def normalize(vector: Sequence[float]) -> Vector:
    length = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / length for v in vector]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """For unit vectors, the dot product."""
    return sum(x * y for x, y in zip(a, b, strict=True))


def _stem(word: str) -> str:
    for suffix in ("ation", "ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def tokens(text: str) -> list[str]:
    """Lower-cased word stems; camelCase and PascalCase identifiers are split."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9]+|\d{3,}", spaced)
    return [_stem(w.lower()) for w in words if w.lower() not in STOPWORDS]


class HashingEmbedder:
    def __init__(self, dimensions: int = 512):
        self.dimensions = dimensions
        self.name = f"hashing-{dimensions}"

    def _embed(self, text: str) -> Vector:
        vector = [0.0] * self.dimensions
        words = tokens(text)
        for feature in words + [f"{a} {b}" for a, b in zip(words, words[1:], strict=False)]:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "little") % self.dimensions
            vector[bucket] += 1.0 if digest[4] & 1 else -1.0
        return normalize(vector)

    def embed_documents(self, texts: Sequence[str]) -> list[Vector]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> Vector:
        return self._embed(text)


def batches(texts: Sequence[str]) -> list[list[str]]:
    """Consecutive batches of at most BATCH_SIZE texts and about BATCH_TOKENS tokens."""
    out: list[list[str]] = []
    current: list[str] = []
    tokens_in_batch = 0
    for text in texts:
        estimate = len(text) // 3 + 1
        if current and (len(current) >= BATCH_SIZE or tokens_in_batch + estimate > BATCH_TOKENS):
            out.append(current)
            current, tokens_in_batch = [], 0
        current.append(text)
        tokens_in_batch += estimate
    return [*out, current] if current else out


def _retry_delay(error: Exception) -> float | None:
    """Seconds Google asks us to wait on a per-minute 429; None for anything else."""
    text = str(error)
    if "429" not in text or "PerDay" in text:
        return None
    match = re.search(r"retry in ([\d.]+)s", text)
    return float(match.group(1)) + 1.0 if match else PACE_SECONDS


class GeminiEmbedder:
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-embedding-001",
        dimensions: int = 768,
        sleep: Callable[[float], None] = time.sleep,
    ):
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._sleep = sleep
        self._last_batch = -PACE_SECONDS
        self.model = model
        self.dimensions = dimensions
        self.name = f"{model}-{dimensions}"

    def _send(self, batch: list[str], config: object) -> list[Vector]:
        last_error: Exception | None = None
        for _ in range(MAX_RATE_LIMIT_WAITS):
            wait = self._last_batch + PACE_SECONDS - time.monotonic()
            if len(batch) > 1 and wait > 0:
                self._sleep(wait)
            self._last_batch = time.monotonic()
            try:
                response = self._client.models.embed_content(model=self.model, contents=batch, config=config)
            except Exception as exc:
                delay = _retry_delay(exc)
                if delay is None:
                    raise
                last_error = exc
                self._sleep(delay)
                continue
            # Truncated (non-3072) Gemini embeddings are not unit length; normalise them.
            return [normalize(e.values) for e in response.embeddings]
        raise RuntimeError(
            f"Gemini embeddings still rate-limited after {MAX_RATE_LIMIT_WAITS} waits: {last_error}"
        ) from last_error

    def _embed(self, texts: Sequence[str], task_type: str) -> list[Vector]:
        from google.genai import types

        config = types.EmbedContentConfig(output_dimensionality=self.dimensions, task_type=task_type)
        vectors: list[Vector] = []
        for batch in batches(texts):
            vectors.extend(self._send(batch, config))
        return vectors

    def embed_documents(self, texts: Sequence[str]) -> list[Vector]:
        return self._embed(texts, "RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> Vector:
        return self._embed([text], "RETRIEVAL_QUERY")[0]
