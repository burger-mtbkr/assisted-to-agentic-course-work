"""The derived index: documents, chunks with vectors, entities and relationships, in SQLite.

Everything here can be rebuilt from the codebase and the notes (`librarian index`);
nothing in it is a source of truth. Vectors are JSON lists searched with a plain
cosine scan - a few hundred chunks need no vector extension.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Iterator, Sequence
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from librarian_agent.embeddings import Vector, cosine

SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE documents (path TEXT PRIMARY KEY, kind TEXT NOT NULL, sha1 TEXT NOT NULL);
CREATE TABLE chunks (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,          -- a codebase path, or note:<id>
    kind TEXT NOT NULL,            -- doc, source, test, knowledge, contract, config, note
    start_line INTEGER, end_line INTEGER,
    text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'current',  -- notes only: current, uncertain, superseded, archived
    vector TEXT NOT NULL
);
CREATE TABLE entities (
    id TEXT PRIMARY KEY,           -- term:<id>, area:<id>, file:<path>, note:<id>
    kind TEXT NOT NULL, name TEXT NOT NULL, aliases TEXT NOT NULL DEFAULT '[]',
    summary TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT ''
);
CREATE TABLE relationships (
    src TEXT NOT NULL, rel TEXT NOT NULL, dst TEXT NOT NULL,
    evidence TEXT NOT NULL, confidence REAL NOT NULL,
    PRIMARY KEY (src, rel, dst)
);
"""


class IndexUnavailable(RuntimeError):
    """The index is missing, or was built by a different embedder than the one in use."""


@dataclass(frozen=True)
class Chunk:
    source: str
    kind: str
    start_line: int | None
    end_line: int | None
    text: str
    status: str = "current"


@dataclass(frozen=True)
class Edge:
    src: str
    rel: str
    dst: str
    evidence: str
    confidence: float


@contextmanager
def connect(path: Path) -> Iterator[sqlite3.Connection]:
    """A connection that commits on success and is always closed (Windows cannot replace an
    open database file)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


class EmbeddingCache:
    """Vectors by (embedder, sha1 of text), in their own file so they outlive any rebuild:
    re-indexing embeds only what changed, which matters on a free tier that allows 100
    embedded texts a minute."""

    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        with connect(self.path) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS vectors (embedder TEXT NOT NULL, sha1 TEXT NOT NULL, "
                "vector TEXT NOT NULL, PRIMARY KEY (embedder, sha1))"
            )
            yield db

    def get(self, embedder_name: str, shas: Sequence[str]) -> dict[str, Vector]:
        wanted = set(shas)
        with self._connect() as db:
            rows = db.execute(
                "SELECT sha1, vector FROM vectors WHERE embedder = ?", (embedder_name,)
            ).fetchall()
        return {r["sha1"]: json.loads(r["vector"]) for r in rows if r["sha1"] in wanted}

    def put(self, embedder_name: str, vectors: dict[str, Vector]) -> None:
        with self._connect() as db:
            db.executemany(
                "INSERT OR REPLACE INTO vectors VALUES (?, ?, ?)",
                [(embedder_name, sha, json.dumps(v)) for sha, v in vectors.items()],
            )


class MemoryIndex:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _connect(self) -> AbstractContextManager[sqlite3.Connection]:
        return connect(self.db_path)

    # -- building ---------------------------------------------------------------

    def reset(self) -> None:
        """Drop and recreate everything. The index is unusable until `seal`."""
        with self._connect() as db:
            for table in ("meta", "documents", "chunks", "entities", "relationships"):
                db.execute(f"DROP TABLE IF EXISTS {table}")
            db.executescript(SCHEMA)

    def seal(self, embedder_name: str) -> None:
        """Mark a finished build usable, recording which embedder made its vectors."""
        with self._connect() as db:
            db.executemany(
                "INSERT OR REPLACE INTO meta VALUES (?, ?)",
                [
                    ("embedder", embedder_name),
                    ("indexed_at", datetime.now(UTC).isoformat(timespec="seconds")),
                ],
            )

    def add_document(self, path: str, kind: str, sha1: str) -> None:
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO documents VALUES (?, ?, ?)", (path, kind, sha1))

    def add_chunks(self, chunks: Sequence[Chunk], vectors: Sequence[Vector]) -> None:
        with self._connect() as db:
            db.executemany(
                "INSERT INTO chunks (source, kind, start_line, end_line, text, status, vector) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (c.source, c.kind, c.start_line, c.end_line, c.text, c.status, json.dumps(v))
                    for c, v in zip(chunks, vectors, strict=True)
                ],
            )

    def replace_note_chunk(self, chunk: Chunk, vector: Vector) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM chunks WHERE source = ?", (chunk.source,))
        self.add_chunks([chunk], [vector])

    def set_note_status(self, note_id: str, status: str) -> None:
        with self._connect() as db:
            db.execute("UPDATE chunks SET status = ? WHERE source = ?", (status, f"note:{note_id}"))

    def add_entity(
        self,
        entity_id: str,
        kind: str,
        name: str,
        aliases: Iterable[str] = (),
        summary: str = "",
        source: str = "",
    ) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO entities VALUES (?, ?, ?, ?, ?, ?)",
                (entity_id, kind, name, json.dumps(list(aliases)), summary, source),
            )

    def add_edges(self, edges: Iterable[Edge]) -> None:
        with self._connect() as db:
            db.executemany(
                "INSERT OR REPLACE INTO relationships VALUES (?, ?, ?, ?, ?)",
                [(e.src, e.rel, e.dst, e.evidence, e.confidence) for e in edges],
            )

    # -- reading ----------------------------------------------------------------

    def meta(self) -> dict[str, str]:
        if not self.db_path.is_file():
            return {}
        with self._connect() as db:
            try:
                return {row["key"]: row["value"] for row in db.execute("SELECT key, value FROM meta")}
            except sqlite3.OperationalError:
                return {}

    def require(self, embedder_name: str) -> None:
        built_by = self.meta().get("embedder")
        if built_by is None:
            raise IndexUnavailable("No index yet. Run `librarian index` first.")
        if built_by != embedder_name:
            raise IndexUnavailable(
                f"The index was built with {built_by}, but {embedder_name} is configured; "
                "vectors from different embedders cannot be compared. Re-run `librarian index`."
            )

    def search(self, query: Vector, include_superseded: bool = False) -> list[tuple[float, Chunk]]:
        """Every chunk scored against the query, best first."""
        hidden = () if include_superseded else ("superseded", "archived")
        with self._connect() as db:
            rows = db.execute(
                "SELECT source, kind, start_line, end_line, text, status, vector FROM chunks"
            ).fetchall()
        scored = [
            (
                cosine(query, json.loads(r["vector"])),
                Chunk(r["source"], r["kind"], r["start_line"], r["end_line"], r["text"], r["status"]),
            )
            for r in rows
            if r["status"] not in hidden
        ]
        return sorted(scored, key=lambda pair: pair[0], reverse=True)

    def entities(self, kinds: Iterable[str] | None = None) -> list[sqlite3.Row]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM entities").fetchall()
        wanted = set(kinds) if kinds is not None else None
        return [r for r in rows if wanted is None or r["kind"] in wanted]

    def edges_touching(self, ids: Iterable[str], min_confidence: float = 0.0) -> list[Edge]:
        wanted = list(dict.fromkeys(ids))
        if not wanted:
            return []
        marks = ",".join("?" * len(wanted))
        with self._connect() as db:
            rows = db.execute(
                f"SELECT * FROM relationships WHERE (src IN ({marks}) OR dst IN ({marks})) "
                "AND confidence >= ? ORDER BY confidence DESC, rel, src, dst",
                [*wanted, *wanted, min_confidence],
            ).fetchall()
        return [Edge(r["src"], r["rel"], r["dst"], r["evidence"], r["confidence"]) for r in rows]

    def note_statuses(self) -> dict[str, str]:
        """Each indexed note's status, as the index knows it."""
        with self._connect() as db:
            rows = db.execute("SELECT source, status FROM chunks WHERE kind = 'note'").fetchall()
        return {r["source"].removeprefix("note:"): r["status"] for r in rows}

    def document_sha(self, path: str) -> str | None:
        with self._connect() as db:
            row = db.execute("SELECT sha1 FROM documents WHERE path = ?", (path,)).fetchone()
        return row["sha1"] if row else None

    def stats(self) -> dict[str, object]:
        if not self.meta():
            return {}
        with self._connect() as db:

            def counts(sql: str) -> dict[str, int]:
                return {row[0]: row[1] for row in db.execute(sql)}

            return {
                **self.meta(),
                "documents": db.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
                "chunks_by_kind": counts("SELECT kind, COUNT(*) FROM chunks GROUP BY kind ORDER BY kind"),
                "entities_by_kind": counts("SELECT kind, COUNT(*) FROM entities GROUP BY kind ORDER BY kind"),
                "relationships_by_type": counts(
                    "SELECT rel, COUNT(*) FROM relationships GROUP BY rel ORDER BY rel"
                ),
            }

    def documents(self) -> dict[str, str]:
        with self._connect() as db:
            return {row["path"]: row["sha1"] for row in db.execute("SELECT path, sha1 FROM documents")}
