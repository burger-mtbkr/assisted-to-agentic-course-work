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
                                   (only sources that are indexed files, only known terms)
  note -supersedes-> note          a correction                        1.0
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import yaml
from agent_kit.mount import visible_files

from librarian_agent.embeddings import Embedder, Vector, batches
from librarian_agent.notes import MemoryNote, NoteStore
from librarian_agent.store import Chunk, Edge, EmbeddingCache, MemoryIndex

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
        if name.endswith("Tests.cs"):
            target = name.removesuffix("Tests.cs") + ".cs"
        elif ".test." in name:
            target = name.replace(".test.", ".")
        else:
            continue  # a helper in the test project (GlobalUsings, fixtures) tests nothing by name
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


def embed(texts: list[str], embedder: Embedder, cache: EmbeddingCache) -> list[Vector]:
    """Document vectors, from the cache where the exact text was embedded before. New
    vectors are cached batch by batch, so an interrupted build keeps what it paid for."""
    shas = [hashlib.sha1(t.encode("utf-8")).hexdigest() for t in texts]
    known = cache.get(embedder.name, shas)
    text_for = dict(zip(shas, texts, strict=True))
    missing = [text_for[sha] for sha in dict.fromkeys(shas) if sha not in known]
    for batch in batches(missing):
        fresh = {
            hashlib.sha1(t.encode("utf-8")).hexdigest(): v
            for t, v in zip(batch, embedder.embed_documents(batch), strict=True)
        }
        cache.put(embedder.name, fresh)
        known |= fresh
    return [known[sha] for sha in shas]


def note_chunk(note: MemoryNote) -> Chunk:
    return Chunk(f"note:{note.id}", "note", None, None, note.embedding_text(), note.status)


def note_edges(note: MemoryNote, files: set[str], terms: set[str]) -> list[Edge]:
    """A note's links into the graph - only to files the index holds and terms it knows;
    user and commit sources stay provenance on the note itself."""
    evidence = f"note {note.id}"
    node = f"note:{note.id}"
    edges = [
        Edge(node, "explains", f"file:{s}", evidence, note.confidence) for s in note.sources if s in files
    ]
    edges += [
        Edge(node, "explains", f"term:{e}", evidence, note.confidence) for e in note.entities if e in terms
    ]
    edges += [Edge(node, "supersedes", f"note:{old}", evidence, 1.0) for old in note.supersedes]
    return edges


def _note_entity(index: MemoryIndex, note: MemoryNote) -> None:
    index.add_entity(
        f"note:{note.id}", "note", note.title, summary=note.statement, source=f"notes/{note.id}.md"
    )


def index_note(note: MemoryNote, index: MemoryIndex, embedder: Embedder, cache: EmbeddingCache) -> None:
    """Add one note to a built index right after it is remembered.

    Statuses and links first, the vector last: if embedding fails, what the index says
    about which notes are current is still right, and only semantic recall of the new
    note is missing until the next `librarian index`.
    """
    for old in note.supersedes:
        index.set_note_status(old, "superseded")
    _note_entity(index, note)
    terms = {e["id"].removeprefix("term:") for e in index.entities(["term"])}
    index.add_edges(note_edges(note, set(index.documents()), terms))
    index.replace_note_chunk(note_chunk(note), embed([note.embedding_text()], embedder, cache)[0])


def build_index(
    codebase: Path,
    knowledge_dir: Path,
    notes: NoteStore,
    index: MemoryIndex,
    embedder: Embedder,
    cache: EmbeddingCache,
) -> IndexReport:
    """Build into a side file and swap it in only when complete: a failed build leaves the
    previous index in place, never a half-filled one."""
    building = MemoryIndex(index.db_path.with_name(index.db_path.stem + ".building.db"))
    building.db_path.unlink(missing_ok=True)
    building.reset()
    paths = [p for p in visible_files(codebase) if indexable(p)]
    chunks: list[Chunk] = []
    for path in paths:
        raw = (codebase / path).read_bytes()
        building.add_document(path, kind_of(path), hashlib.sha1(raw).hexdigest())
        building.add_entity(f"file:{path}", "file", PurePosixPath(path).name, source=path)
        lines = raw.decode("utf-8", "replace").splitlines()
        for start, end in chunk_lines(lines, markdown=path.endswith(".md")):
            text = "\n".join(lines[start - 1 : end]).strip()
            if text:
                chunks.append(Chunk(path, kind_of(path), start, end, f"{path} lines {start}-{end}\n{text}"))
    building.add_chunks(chunks, embed([c.text for c in chunks], embedder, cache))
    building.add_edges(tested_in_edges(paths))
    import_knowledge_graph(knowledge_dir, codebase, building)
    all_notes = notes.list()
    if all_notes:
        terms = {e["id"].removeprefix("term:") for e in building.entities(["term"])}
        building.add_chunks(
            [note_chunk(n) for n in all_notes],
            embed([n.embedding_text() for n in all_notes], embedder, cache),
        )
        for note in all_notes:
            _note_entity(building, note)
            building.add_edges(note_edges(note, set(paths), terms))
    building.seal(embedder.name)
    os.replace(building.db_path, index.db_path)
    stats = index.stats()
    return IndexReport(
        documents=len(paths),
        chunks=len(chunks),
        entities=sum(stats["entities_by_kind"].values()),
        relationships=sum(stats["relationships_by_type"].values()),
        notes=len(all_notes),
    )
