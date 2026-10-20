"""Opt-in: real Gemini embeddings on the recall case the deterministic embedder cannot do.

Run with `LIBRARIAN_LIVE=1 uv run --project librarian-agent pytest librarian-agent -m live`.
Costs a few free-tier embedding requests.
"""

import os

import pytest

from librarian_agent.config import LibrarianConfig
from librarian_agent.embeddings import GeminiEmbedder, HashingEmbedder, cosine

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get("LIBRARIAN_LIVE") != "1", reason="set LIBRARIAN_LIVE=1 to call Gemini"),
]

STORED = "Config sets are validated at write time because callers need fast reads."
DISTRACTOR = "The admin UI is plain TypeScript with no framework and no client-side router."
QUERY = "Why validate before saving?"


def test_meaning_level_recall_beats_word_overlap():
    gemini = GeminiEmbedder(LibrarianConfig.load().require_key())
    stored, distractor = gemini.embed_documents([STORED, DISTRACTOR])
    query = gemini.embed_query(QUERY)
    assert cosine(query, stored) > cosine(query, distractor) + 0.05

    hashing = HashingEmbedder()
    h_stored, h_distractor = hashing.embed_documents([STORED, DISTRACTOR])
    h_query = hashing.embed_query(QUERY)
    # The texts share no word stem ("validate" vs "validated" stem differently), so hashing
    # scores both 0: this recall needs meaning, not word overlap.
    assert cosine(h_query, h_stored) - cosine(h_query, h_distractor) < cosine(query, stored) - cosine(
        query, distractor
    )
