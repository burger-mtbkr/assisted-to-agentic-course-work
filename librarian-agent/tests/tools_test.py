"""The tools layer: every failure is a tool error, and a correction stays consistent even
when the embedding provider fails halfway."""

import json

import pytest
from langchain_core.tools import ToolException

from librarian_agent.embeddings import HashingEmbedder
from librarian_agent.notes import NoteStore
from librarian_agent.store import EmbeddingCache, MemoryIndex
from librarian_agent.tools import LibrarianTools


class BrokenEmbedder(HashingEmbedder):
    """Same name as the index's embedder, but every call fails like a provider outage."""

    def embed_documents(self, texts):
        raise RuntimeError("503 UNAVAILABLE")

    def embed_query(self, text):
        raise RuntimeError("503 UNAVAILABLE")


def tools_for(config, index, embedder=None):
    return LibrarianTools(
        config.codebase_path,
        NoteStore(config.notes_dir),
        index,
        embedder or HashingEmbedder(),
        EmbeddingCache(config.cache_path),
        config.retrievals_dir,
    )


def by_name(tools):
    return {t.name: t for t in tools.as_langchain_tools()}


def test_a_provider_failure_mid_correction_leaves_memory_consistent(config, index):
    tools = tools_for(config, index)
    old = tools.remember_decision("Raw values", "Audit logs store raw values.", "Debugging.", ["user"])
    broken = tools_for(config, index, BrokenEmbedder())
    saved = broken.remember_decision(
        "Hashes", "Audit logs store hashes.", "Secrets.", ["user"], supersedes=[old["remembered"]]
    )
    assert saved["indexed"] is False and "not yet searchable" in saved["warning"]
    statuses = MemoryIndex(config.db_path).note_statuses()
    assert statuses[old["remembered"]] == "superseded"  # file and index agree
    assert tools.notes.read(old["remembered"]).superseded_by == saved["remembered"]
    with pytest.raises(Exception, match="Only a current or uncertain note"):
        broken.remember_decision("Again", "x", "y", ["user"], supersedes=[old["remembered"]])


def test_only_sources_the_index_can_check_lift_the_confidence_cap(config, index):
    tools = tools_for(config, index)
    made_up = tools.remember_decision("A", "s", "r", ["src/Made/Up.cs"], confidence=1.0)
    real = tools.remember_decision(
        "B", "s", "r", ["/codebase/src/Api/Middleware/ErrorMiddleware.cs"], confidence=1.0
    )
    assert made_up["confidence"] == 0.7 and real["confidence"] == 1.0
    assert real["sources"] == ["src/Api/Middleware/ErrorMiddleware.cs"]


def test_unknown_entities_are_kept_but_reported_as_unlinked(config, index):
    saved = tools_for(config, index).remember_decision(
        "C", "s", "r", ["user"], entities=["error_response", "audit logging"]
    )
    assert "audit logging" in saved["not_linked"] and "error_response" not in saved["not_linked"]


def test_marking_a_note_updates_file_and_index(config, index):
    tools = tools_for(config, index)
    saved = tools.remember_decision("D", "s", "r", ["user"])
    assert (
        tools.mark_memory_note(saved["remembered"], "archived", "no longer applies")["status"] == "archived"
    )
    assert MemoryIndex(config.db_path).note_statuses()[saved["remembered"]] == "archived"


def test_a_note_can_be_remembered_as_uncertain(config, index):
    saved = tools_for(config, index).remember_decision("D", "s", "r", ["user"], status="uncertain")
    assert (
        saved["indexed"] and MemoryIndex(config.db_path).note_statuses()[saved["remembered"]] == "uncertain"
    )


def test_every_failure_is_a_tool_error_not_a_crash(config, index):
    tool = by_name(tools_for(config, index))
    blob = tools_for(config, index).history._git("rev-parse", "HEAD:.gitignore")  # a blob, not a commit
    for name, args, message in [
        ("git_show", {"commit": blob.strip()[:12]}, "not a commit in this repository"),
        ("read_memory_note", {"note_id": "../x"}, "not a note id"),
        ("git_log", {"path": ":(top)"}, "not a path inside the codebase"),
    ]:
        with pytest.raises(ToolException, match=message):
            tool[name].func(**args)
    broken = by_name(tools_for(config, index, BrokenEmbedder()))
    with pytest.raises(ToolException, match="retrieve_context failed: RuntimeError: 503"):
        broken["retrieve_context"].func(query="anything")
    assert json.loads(tool["list_memory_notes"].func(status="all"))["notes"] == []
