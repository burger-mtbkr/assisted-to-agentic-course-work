"""Curated indexing: which codebase files become chunks, and which relationships the graph holds.

Indexed: docs, C#/TypeScript source and tests, the knowledge graph YAML, the
OpenAPI contract and appsettings*.json - what explains the system. Not indexed: lock files, project and
solution files, anything git does not track.

Relationships, each with evidence and a confidence:
  term -implemented_in-> file      knowledge graph `source_files`      1.0
  doc -documents-> term            knowledge graph `documentation`     1.0
  area -contains-> term            knowledge graph `area`              1.0
  term -<relationship>-> term      knowledge graph edges               1.0
  file -tested_in-> test file      naming convention (XTests.cs, x.test.ts)  0.9
  note -explains-> file or term    the note's sources and entities     the note's confidence
  note -supersedes-> note          a correction                        1.0
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import yaml
from agent_kit.mount import visible_files

from librarian_agent.embeddings import Embedder, Vector
from librarian_agent.notes import MemoryNote, NoteStore
from librarian_agent.store import Chunk, Edge, MemoryIndex

INDEXED_SUFFIXES = {".md", ".cs", ".ts", ".yaml", ".yml"}
CHUNK_LINES = 60
CHUNK_OVERLAP = 10


@dataclass(frozen=True)
class IndexReport:
    documents: int
    chunks: int
    entities: int
    relationships: int
    notes: int


def kind_of(path: str) -> str:
    pure = PurePosixPath(path)
    if pure.suffix == ".md":
        return "doc"
    if pure.suffix in (".yaml", ".yml"):
        return "knowledge"
    if pure.name == "openapi.json":
        return "contract"
    if pure.name.startswith("appsettings"):
        return "config"
    if ".UnitTests/" in path or ".test." in pure.name:
        return "test"
    return "source"


def indexable(path: str) -> bool:
    pure = PurePosixPath(path)
    wanted = (
        pure.suffix in INDEXED_SUFFIXES or pure.name == "openapi.json" or pure.name.startswith("appsettings")
    )
    return wanted and not pure.name.endswith(".d.ts")


def chunk_lines(lines: list[str], markdown: bool) -> Iterator[tuple[int, int]]:
    """1-based inclusive line ranges. Markdown splits at headings; everything else in
    overlapping windows."""
    if markdown:
        starts = [i for i, line in enumerate(lines) if line.startswith("#")] or [0]
        if starts[0] != 0:
            starts.insert(0, 0)
        for begin, end in zip(starts, [*starts[1:], len(lines)], strict=True):
            for window in range(begin, end, CHUNK_LINES):
                yield window + 1, min(window + CHUNK_LINES, end)
        return
    step = CHUNK_LINES - CHUNK_OVERLAP
    for begin in range(0, max(len(lines) - CHUNK_OVERLAP, 1), step):
        yield begin + 1, min(begin + CHUNK_LINES, len(lines))


def tested_in_edges(paths: list[str]) -> list[Edge]:
    """C# `<Name>Tests.cs` tests `<Name>.cs`; TypeScript `x.test.ts` tests `x.ts`."""
    by_name: dict[str, list[str]] = {}
    for path in paths:
        if kind_of(path) == "source":
            by_name.setdefault(PurePosixPath(path).name, []).append(path)
    edges = []
    for test in (p for p in paths if kind_of(p) == "test"):
        name = PurePosixPath(test).name
        target = (
            name.removesuffix("Tests.cs") + ".cs"
            if name.endswith("Tests.cs")
            else name.replace(".test.", ".")
        )
        for source in by_name.get(target, []):
            edges.append(
                Edge(f"file:{source}", "tested_in", f"file:{test}", f"naming convention: {name}", 0.9)
            )
    return edges


def import_knowledge_graph(knowledge_dir: Path, codebase: Path, index: MemoryIndex) -> None:
    """The Module 5 domain-language graph as entities and edges."""
    if not knowledge_dir.is_dir():
        return
    edges: list[Edge] = []
    for path in sorted(knowledge_dir.glob("nodes/*.y*ml")):
        evidence = path.relative_to(codebase).as_posix() if path.is_relative_to(codebase) else path.name
        for node in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("nodes", []):
            term = f"term:{node['id']}"
            summary = " ".join(
                [node.get("definition", "").strip(), *(f"Warning: {w}" for w in node.get("warnings", []))]
            )
            index.add_entity(term, "term", node["name"], node.get("aliases", []), summary, evidence)
            if area := node.get("area"):
                index.add_entity(f"area:{area}", "area", area.replace("_", " "), source=evidence)
                edges.append(Edge(f"area:{area}", "contains", term, evidence, 1.0))
            edges += [
                Edge(term, "implemented_in", f"file:{f}", evidence, 1.0) for f in node.get("source_files", [])
            ]
            edges += [
                Edge(f"file:{d}", "documents", term, evidence, 1.0) for d in node.get("documentation", [])
            ]
    for path in sorted(knowledge_dir.glob("edges/*.y*ml")):
        evidence = path.relative_to(codebase).as_posix() if path.is_relative_to(codebase) else path.name
        for edge in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("edges", []):
            edges.append(
                Edge(f"term:{edge['from']}", edge["relationship"], f"term:{edge['to']}", evidence, 1.0)
            )
    index.add_edges(edges)


def embed(texts: list[str], embedder: Embedder, index: MemoryIndex) -> list[Vector]:
    """Document vectors, from the cache where the exact text was embedded before."""
    shas = [hashlib.sha1(t.encode("utf-8")).hexdigest() for t in texts]
    known = index.cached_vectors(embedder.name, shas)
    missing = list(dict.fromkeys(sha for sha in shas if sha not in known))
    if missing:
        text_for = dict(zip(shas, texts, strict=True))
        fresh = dict(zip(missing, embedder.embed_documents([text_for[sha] for sha in missing]), strict=True))
        index.cache_vectors(embedder.name, fresh)
        known |= fresh
    return [known[sha] for sha in shas]


def note_chunk(note: MemoryNote) -> Chunk:
    return Chunk(f"note:{note.id}", "note", None, None, note.embedding_text(), note.status)


def note_edges(note: MemoryNote) -> list[Edge]:
    evidence = f"note {note.id}"
    edges = [
        Edge(f"note:{note.id}", "explains", f"file:{s}", evidence, note.confidence) for s in note.sources
    ]
    edges += [
        Edge(f"note:{note.id}", "explains", f"term:{e}", evidence, note.confidence) for e in note.entities
    ]
    edges += [Edge(f"note:{note.id}", "supersedes", f"note:{old}", evidence, 1.0) for old in note.supersedes]
    return edges


def index_note(note: MemoryNote, index: MemoryIndex, embedder: Embedder) -> None:
    """Add or refresh one note without rebuilding everything (used right after remembering)."""
    index.add_entity(
        f"note:{note.id}", "note", note.title, summary=note.statement, source=f"notes/{note.id}.md"
    )
    index.replace_note_chunk(note_chunk(note), embed([note.embedding_text()], embedder, index)[0])
    index.add_edges(note_edges(note))
    for old in note.supersedes:
        index.set_note_status(old, "superseded")


def build_index(
    codebase: Path, knowledge_dir: Path, notes: NoteStore, index: MemoryIndex, embedder: Embedder
) -> IndexReport:
    index.reset(embedder.name)
    paths = [p for p in visible_files(codebase) if indexable(p)]
    chunks: list[Chunk] = []
    for path in paths:
        raw = (codebase / path).read_bytes()
        index.add_document(path, kind_of(path), hashlib.sha1(raw).hexdigest())
        index.add_entity(f"file:{path}", "file", PurePosixPath(path).name, source=path)
        lines = raw.decode("utf-8", "replace").splitlines()
        for start, end in chunk_lines(lines, markdown=path.endswith(".md")):
            text = "\n".join(lines[start - 1 : end]).strip()
            if text:
                chunks.append(Chunk(path, kind_of(path), start, end, f"{path} lines {start}-{end}\n{text}"))
    index.add_chunks(chunks, embed([c.text for c in chunks], embedder, index))
    index.add_edges(tested_in_edges(paths))
    import_knowledge_graph(knowledge_dir, codebase, index)
    all_notes = notes.list()
    if all_notes:
        vectors = embed([n.embedding_text() for n in all_notes], embedder, index)
        index.add_chunks([note_chunk(n) for n in all_notes], vectors)
        for note in all_notes:
            index.add_entity(
                f"note:{note.id}", "note", note.title, summary=note.statement, source=f"notes/{note.id}.md"
            )
            index.add_edges(note_edges(note))
    stats = index.stats()
    return IndexReport(
        documents=len(paths),
        chunks=len(chunks),
        entities=sum(stats["entities_by_kind"].values()),
        relationships=sum(stats["relationships_by_type"].values()),
        notes=len(all_notes),
    )
