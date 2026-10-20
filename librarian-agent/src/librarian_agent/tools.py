"""The Librarian's own tools: one hybrid retrieval call, durable notes, and Git history.

Every tool returns JSON. A refused or failed call raises `ToolException`, which Deep
Agents hands back to the model as an error result rather than ending the turn.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict
from functools import wraps
from pathlib import Path
from typing import Any

from langchain_core.tools import StructuredTool, ToolException

from librarian_agent.embeddings import Embedder
from librarian_agent.history import GitHistory, HistoryError
from librarian_agent.indexer import index_note
from librarian_agent.notes import STATUSES, NoteError, NoteStore
from librarian_agent.retrieval import retrieve_context
from librarian_agent.store import IndexUnavailable, MemoryIndex

REFUSALS = (NoteError, HistoryError, IndexUnavailable)


def _json_tool(func: Callable[..., Any]) -> Callable[..., str]:
    @wraps(func)
    def run(*args: Any, **kwargs: Any) -> str:
        try:
            return json.dumps(func(*args, **kwargs), ensure_ascii=False, indent=1)
        except REFUSALS as exc:
            raise ToolException(str(exc)) from exc

    return run


class LibrarianTools:
    def __init__(
        self, codebase: Path, notes: NoteStore, index: MemoryIndex, embedder: Embedder, retrievals_dir: Path
    ):
        self.codebase = codebase
        self.notes = notes
        self.index = index
        self.embedder = embedder
        self.retrievals_dir = retrievals_dir
        self.history = GitHistory(codebase)

    def retrieve_context(self, query: str, include_superseded: bool = False) -> dict[str, Any]:
        return retrieve_context(
            query,
            index=self.index,
            embedder=self.embedder,
            notes=self.notes,
            codebase=self.codebase,
            retrievals_dir=self.retrievals_dir,
            include_superseded=include_superseded,
        )

    def remember_decision(
        self,
        title: str,
        statement: str,
        rationale: str,
        sources: list[str],
        confidence: float = 0.7,
        entities: list[str] | None = None,
        supersedes: list[str] | None = None,
    ) -> dict[str, Any]:
        note = self.notes.remember(
            title=title,
            statement=statement,
            rationale=rationale,
            sources=sources,
            confidence=confidence,
            entities=entities or [],
            supersedes=supersedes or [],
        )
        result: dict[str, Any] = {
            "remembered": note.id,
            "file": f"notes/{note.id}.md",
            "superseded": note.supersedes,
        }
        try:
            self.index.require(self.embedder.name)
            index_note(note, self.index, self.embedder)
            result["indexed"] = True
        except IndexUnavailable as exc:
            result |= {"indexed": False, "note": f"Saved, but not yet searchable: {exc}"}
        return result

    def list_memory_notes(self, status: str = "current") -> dict[str, Any]:
        if status != "all" and status not in STATUSES:
            raise NoteError(f"status is one of {', '.join(STATUSES)} or 'all'.")
        notes = self.notes.list(None if status == "all" else status)
        return {
            "status": status,
            "notes": [
                {k: getattr(n, k) for k in ("id", "title", "status", "confidence", "superseded_by")}
                for n in notes
            ],
        }

    def read_memory_note(self, note_id: str) -> dict[str, Any]:
        return asdict(self.notes.read(note_id))

    def git_log(self, path: str = "", limit: int = 15) -> dict[str, Any]:
        return self.history.log(path, limit)

    def git_show(self, commit: str) -> dict[str, Any]:
        return self.history.show(commit)

    def file_history(self, path: str) -> dict[str, Any]:
        return self.history.file_history(path)

    def as_langchain_tools(self) -> list[StructuredTool]:
        described = {
            "retrieve_context": (
                "The primary way to find context: one call that combines semantic recall over indexed docs, "
                "source, tests and memory notes with knowledge-graph relationships. Returns semantic_hits, "
                "entity_hits, graph_expansion, memories (current notes), recommended_context (what to read, "
                "and why) and gaps. Call it before reading source broadly. Superseded notes are left out "
                "unless include_superseded is true (use that only for 'what did we think before?')."
            ),
            "remember_decision": (
                "Save a durable decision note to the Librarian's memory (never to the codebase). Use when "
                "the user asks you to remember something, or corrects an earlier memory - then pass the old "
                "note ids in `supersedes`. sources: codebase paths, commit hashes, or 'user' when the user "
                "stated it (the store dates it). confidence 0-1: how well the sources support it."
            ),
            "list_memory_notes": (
                "List remembered notes by status: current (default), uncertain, superseded, archived, or all."
            ),
            "read_memory_note": "Read one note in full: statement, rationale, sources, status, history.",
            "git_log": (
                "Recent commits touching the codebase, or one path in it (episodic memory: what changed, "
                "when, by whom). Paths are relative to the codebase root."
            ),
            "git_show": "One commit's message, the codebase files it changed and its diff (compacted).",
            "file_history": "Commits that touched one file, following renames.",
        }
        return [
            StructuredTool.from_function(
                func=_json_tool(getattr(self, name)), name=name, description=text, handle_tool_error=True
            )
            for name, text in described.items()
        ]
