"""Hybrid retrieval: semantic hits, entity seeds, graph expansion, gaps, supersession, artifacts."""

import json

import pytest
from conftest import read_jsonl

from librarian_agent.embeddings import HashingEmbedder
from librarian_agent.indexer import index_note
from librarian_agent.retrieval import (
    RELATIVE_FLOOR,
    SEMANTIC_K,
    match_entities,
    recommend,
    retrieve_context,
    select_semantic,
)
from librarian_agent.store import Chunk, Edge


def retrieve(config, notes, index, query, **kwargs):
    return retrieve_context(
        query,
        index=index,
        embedder=HashingEmbedder(),
        notes=notes,
        codebase=config.codebase_path,
        retrievals_dir=config.retrievals_dir,
        **kwargs,
    )


def remember(notes, index, **fields):
    note = notes.remember(**fields)
    index_note(note, index, HashingEmbedder())
    return note


AUDIT = {
    "title": "Audit log stores raw values",
    "statement": "Audit logging stores the raw old and new configuration values.",
    "rationale": "Easier debugging.",
    "sources": ["user, 2026-10-20"],
}


def test_a_why_question_returns_the_note_the_source_and_the_graph(config, notes, index):
    note = remember(
        notes,
        index,
        title="Duplicates are 409 Conflict",
        statement="Duplicate names map to 409 Conflict in ErrorMiddleware.",
        rationale="A duplicate conflicts with existing state; it is not malformed input.",
        sources=["src/Api/Middleware/ErrorMiddleware.cs"],
        entities=["error_response"],
        confidence=0.9,
    )
    result = retrieve(config, notes, index, "Why do duplicate names return 409 from the ErrorMiddleware?")

    assert set(result) >= {"semantic_hits", "entity_hits", "graph_expansion", "recommended_context", "gaps"}
    sources = [h["source"] for h in result["semantic_hits"]]
    assert f"note:{note.id}" in sources and "src/Api/Middleware/ErrorMiddleware.cs" in sources
    assert result["memories"][0]["id"] == note.id and result["memories"][0]["confidence"] == 0.9
    assert {"file:src/Api/Middleware/ErrorMiddleware.cs"} <= {h["id"] for h in result["entity_hits"]}
    edges = {(e["src"], e["rel"], e["dst"]) for e in result["graph_expansion"]}
    assert (
        "file:src/Api/Middleware/ErrorMiddleware.cs",
        "tested_in",
        "file:src/Api.UnitTests/Middleware/ErrorMiddlewareTests.cs",
    ) in edges
    assert all(e["evidence"] and e["confidence"] >= 0.6 for e in result["graph_expansion"])
    recommended = [c["source"] for c in result["recommended_context"]]
    assert "src/Api.UnitTests/Middleware/ErrorMiddlewareTests.cs" in recommended
    assert any("does not search Git history" in g for g in result["gaps"])
    assert not any("No current memory note" in g for g in result["gaps"])


def test_prose_does_not_match_files_but_identifiers_and_terms_do(index):
    assert [h["id"] for h in match_entities("how do flags work?", index)] == ["term:feature_flag"]
    named = {h["id"] for h in match_entities("Check ErrorMiddleware and api.ts", index)}
    assert named == {"file:src/Api/Middleware/ErrorMiddleware.cs", "file:ui/src/api.ts"}
    assert match_entities("the error middleware", index) == []


def test_superseded_memories_are_left_out_of_current_answers(config, notes, index):
    old = remember(notes, index, **AUDIT)
    new = remember(
        notes,
        index,
        title="Audit log stores hashes",
        statement="Audit logging stores hashes of the old and new configuration values, not raw values.",
        rationale="Raw values can be secrets.",
        sources=["user, 2026-10-20"],
        supersedes=[old.id],
    )
    current = retrieve(config, notes, index, "What does audit logging store for configuration values?")
    assert [m["id"] for m in current["memories"]] == [new.id]
    assert any(f"Left out note:{old.id} because it is superseded" in g for g in current["gaps"])

    history = retrieve(config, notes, index, "What did audit logging used to store?", include_superseded=True)
    by_id = {m["id"]: m for m in history["memories"]}
    assert by_id[old.id]["superseded_by"] == new.id
    assert any(f"note:{old.id} is superseded by note:{new.id}" in g for g in history["gaps"])


def test_gaps_name_missing_memory_missing_tests_and_stale_files(config, notes, index):
    (config.codebase_path / "src/Api/Models/Flag.cs").write_text(
        "public class Flag { int Changed; }\n", encoding="utf-8"
    )
    result = retrieve(config, notes, index, "How is a feature flag modelled in Flag.cs?")
    gaps = "\n".join(result["gaps"])
    assert "No current memory note matched" in gaps
    assert "No test file follows the naming convention for any file implementing term:feature_flag" in gaps
    assert "src/Api/Models/Flag.cs changed since it was indexed" in gaps


def test_every_retrieval_leaves_an_artifact_and_a_log_line(config, notes, index):
    result = retrieve(config, notes, index, "Where is the error contract documented?")
    artifact = json.loads(open(result["artifact"], encoding="utf-8").read())
    assert artifact["query"] == "Where is the error contract documented?" and artifact["timestamp"]
    assert artifact["recommended_context"] == result["recommended_context"]
    [line] = read_jsonl(config.retrievals_dir / "retrievals.jsonl")
    assert line["query"] == result["query"] and line["gaps"] == len(result["gaps"])


def chunk(source, status="current"):
    return Chunk(source, "doc", 1, 2, source, status)


def test_selection_caps_each_source_and_drops_weak_tails():
    scored = [
        (0.9, chunk("a")),
        (0.89, chunk("a")),
        (0.88, chunk("a")),
        (0.87, chunk("b")),
        (0.9 * RELATIVE_FLOOR - 0.01, chunk("c")),
    ]
    kept, hidden = select_semantic(scored)
    assert [c.source for _, c in kept] == ["a", "a", "b"] and hidden == []


def test_selection_sets_aside_superseded_notes_unless_history_is_asked_for():
    scored = [(0.95, chunk("note:old", "superseded")), (0.9, chunk("note:new"))]
    kept, hidden = select_semantic(scored)
    assert [c.source for _, c in kept] == ["note:new"] and [c.source for _, c in hidden] == ["note:old"]
    kept, hidden = select_semantic(scored, include_superseded=True)
    assert [c.source for _, c in kept] == ["note:old", "note:new"] and hidden == []


@pytest.mark.parametrize("count", [SEMANTIC_K + 5])
def test_selection_returns_at_most_k(count):
    kept, _ = select_semantic([(1.0, chunk(f"s{i}")) for i in range(count)])
    assert len(kept) == SEMANTIC_K


def test_a_source_ranks_by_its_best_evidence_and_graph_reach_inherits_a_discounted_score():
    semantic = [
        (0.8, Chunk("note:n", "note", None, None, "n")),
        (0.7, chunk("big.json")),
        (0.69, chunk("big.json")),
    ]
    graph = [
        Edge("note:n", "explains", "file:src/Middleware.cs", "note n", 0.9),
        Edge("file:src/Middleware.cs", "tested_in", "file:tests/MiddlewareTests.cs", "naming", 0.9),
    ]
    ranked = {e["source"]: e["score"] for e in recommend(semantic, set(), graph)}
    assert ranked["note:n"] == 0.8 and ranked["big.json"] == 0.7  # not 1.39: two weak chunks do not add up
    assert ranked["src/Middleware.cs"] == 0.72 and ranked["tests/MiddlewareTests.cs"] == 0.648
    assert list(ranked)[0] == "note:n"
