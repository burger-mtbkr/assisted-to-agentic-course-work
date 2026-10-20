"""Embedders: the deterministic one used in tests, and the Gemini one's pacing and retries."""

import math
from types import SimpleNamespace

import pytest

from librarian_agent.embeddings import (
    BATCH_SIZE,
    BATCH_TOKENS,
    GeminiEmbedder,
    HashingEmbedder,
    _retry_delay,
    batches,
    cosine,
    tokens,
)


def test_tokens_split_identifiers_stem_words_and_keep_status_codes():
    assert tokens("Why does ErrorMiddleware return 409 for duplicates?") == [
        "error",
        "middleware",
        "return",
        "409",
        "duplicat",
    ]


def test_hashing_vectors_are_deterministic_unit_length_and_meaningful():
    embedder = HashingEmbedder()
    a, b, c = embedder.embed_documents(
        [
            "Duplicate application names return 409 Conflict.",
            "A duplicate name gives a 409 conflict response.",
            "The admin UI is plain TypeScript.",
        ]
    )
    assert a == embedder.embed_documents(["Duplicate application names return 409 Conflict."])[0]
    assert math.isclose(sum(v * v for v in a), 1.0)
    assert cosine(a, b) > cosine(a, c)
    assert embedder.embed_query("x") == embedder.embed_documents(["x"])[0]


class FakeModels:
    def __init__(self, failures):
        self.failures = list(failures)
        self.batches = []

    def embed_content(self, model, contents, config):
        if self.failures:
            raise self.failures.pop(0)
        self.batches.append(list(contents))
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[3.0, 4.0]) for _ in contents])


def gemini(failures=()):
    sleeps = []
    embedder = GeminiEmbedder("unused", dimensions=2, sleep=sleeps.append)
    embedder._client = SimpleNamespace(models=FakeModels(failures))
    return embedder, sleeps


def test_gemini_batches_paces_and_normalises():
    embedder, sleeps = gemini()
    vectors = embedder.embed_documents([f"t{i}" for i in range(BATCH_SIZE + 5)])
    assert [len(b) for b in embedder._client.models.batches] == [BATCH_SIZE, 5]
    assert len(sleeps) == 1 and 50 < sleeps[0] <= 61  # waited before the second batch
    assert vectors[0] == [0.6, 0.8]
    assert embedder.name == "gemini-embedding-001-2"


def test_batches_respect_both_the_count_and_the_token_budget():
    assert [len(b) for b in batches(["x"] * (BATCH_SIZE + 1))] == [BATCH_SIZE, 1]
    big = "y" * (BATCH_TOKENS * 3 // 2)  # about half the token budget each
    assert [len(b) for b in batches([big, big, big])] == [1, 1, 1]
    assert batches([]) == []


def test_gemini_waits_out_a_per_minute_limit_then_succeeds():
    per_minute = RuntimeError("429 RESOURCE_EXHAUSTED ... PerMinute ... Please retry in 16.1s.")
    embedder, sleeps = gemini([per_minute])
    assert embedder.embed_query("q") == [0.6, 0.8]
    assert sleeps == [pytest.approx(17.1)]


def test_gemini_does_not_retry_a_spent_daily_quota_or_other_errors():
    per_day = RuntimeError("429 RESOURCE_EXHAUSTED quotaId GenerateRequestsPerDayPerProjectPerModel-FreeTier")
    with pytest.raises(RuntimeError, match="PerDay"):
        gemini([per_day])[0].embed_query("q")
    with pytest.raises(ValueError):
        gemini([ValueError("bad request")])[0].embed_query("q")
    assert _retry_delay(RuntimeError("429 PerMinute")) == 61.0
