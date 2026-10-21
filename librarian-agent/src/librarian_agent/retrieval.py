"""Hybrid retrieval: one call that combines semantic recall, entity matching, graph
expansion, provenance and gaps - and leaves a JSON artifact of exactly what it returned.

The model gets one context tool instead of a handful of low-level memory tools: the
choice of which memory to consult is made here, deterministically, and is reviewable.
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from librarian_agent.embeddings import Embedder
from librarian_agent.notes import NoteError, NoteStore, slug
from librarian_agent.store import Chunk, Edge, MemoryIndex

SEMANTIC_K = 8
PER_SOURCE = 2  # tuned: without a cap one long doc fills every slot (see the Module 8 journal)
# Tuned on real queries (Module 8 journal). Raw scores mean different things per
# embedder: Gemini packs them into 0.55-0.8, the hashing embedder spreads them over
# 0.0-0.5. So a hit must clear both half the best score and the corpus mean plus one
# standard deviation - "better than a typical chunk" - whichever is higher.
RELATIVE_FLOOR = 0.5
# Best score fewer than this many standard deviations above the corpus mean: weak evidence.
# Measured on config-service with Gemini: answerable questions 3.5-7.4, an off-topic one
# ("how do I bake sourdough bread?") 2.8.
WEAK_EVIDENCE_SIGMAS = 3.0
# Below this many chunks, a mean and standard deviation describe nothing useful.
MIN_CORPUS = 30
MIN_EDGE_CONFIDENCE = 0.6
GRAPH_DISCOUNT = 0.9
MAX_EDGES = 30
SNIPPET_CHARS = 400
HISTORY_QUESTION = re.compile(r"\b(why|when|changed?|history|decid\w*|introduc\w*|before|used to)\b", re.I)


def strength(scored: list[tuple[float, Chunk]]) -> float | None:
    """How far the best score stands above the corpus, in standard deviations (None when the
    corpus is too small to say). The best is the best live chunk: a superseded or archived
    note that matches well is not evidence for the answer."""
    scores = [score for score, _ in scored]
    best = next((score for score, chunk in scored if chunk.status not in ("superseded", "archived")), None)
    if len(scores) < MIN_CORPUS or best is None:
        return None
    spread = statistics.pstdev(scores) or 1e-9
    return (best - statistics.fmean(scores)) / spread


def select_semantic(
    scored: list[tuple[float, Chunk]], include_superseded: bool = False
) -> tuple[list[tuple[float, Chunk]], list[tuple[float, Chunk]]]:
    """Best-first hits, at most PER_SOURCE per source, above the floor (see RELATIVE_FLOOR)
    - plus, separately, the superseded or archived notes that would have made the cut."""

    def stale(chunk: Chunk) -> bool:
        return not include_superseded and chunk.status in ("superseded", "archived")

    kept: list[tuple[float, Chunk]] = []
    hidden: list[tuple[float, Chunk]] = []
    per_source: dict[str, int] = {}
    scores = [score for score, _ in scored]
    top = next((score for score, chunk in scored if not stale(chunk)), 0.0)
    floor = top * RELATIVE_FLOOR
    if len(scores) >= MIN_CORPUS:
        # Never above the best hit: a flat distribution is reported as weak evidence instead.
        floor = min(top, max(floor, statistics.fmean(scores) + statistics.pstdev(scores)))
    for score, chunk in scored:
        if len(kept) >= SEMANTIC_K or score < floor:
            break
        if per_source.get(chunk.source, 0) >= PER_SOURCE:
            continue
        if stale(chunk):
            hidden.append((score, chunk))
            continue
        per_source[chunk.source] = per_source.get(chunk.source, 0) + 1
        kept.append((score, chunk))
    return kept, hidden


def _identifier(word: str) -> bool:
    """Code-shaped, not prose: a file name (`api.ts`) or a multi-word PascalCase type."""
    return "." in word or (word[:1].isupper() and any(c.isupper() for c in word[1:]))


def match_entities(query: str, index: MemoryIndex) -> list[dict[str, str]]:
    """Terms named (or aliased) in the question - with their knowledge-graph definition and
    warnings - and files it names as identifiers.

    File names are matched only when typed like code: the prose word "application"
    must not pull in Application.cs, but "ErrorMiddleware" or "api.ts" should.
    """
    lowered = query.lower()
    identifiers = {w for w in re.findall(r"[A-Za-z][A-Za-z0-9_.]*[A-Za-z0-9]", query) if _identifier(w)}
    hits = []
    for entity in index.entities(["term"]):
        for name in [entity["name"], *json.loads(entity["aliases"])]:
            if len(name) >= 3 and re.search(rf"\b{re.escape(name.lower())}(?:s|es)?\b", lowered):
                hits.append(
                    {
                        "id": entity["id"],
                        "name": entity["name"],
                        "matched_by": f"question mentions {name!r}",
                        "knowledge": entity["summary"],
                        "source": entity["source"],
                    }
                )
                break
    for entity in index.entities(["file"]):
        path = PurePosixPath(entity["source"])
        if path.stem in identifiers or path.name in identifiers:
            hits.append(
                {"id": entity["id"], "name": entity["source"], "matched_by": f"question names {path.stem!r}"}
            )
    return hits


def expand(seeds: list[str], named: set[str], stale: set[str], index: MemoryIndex) -> list[Edge]:
    """One hop from every seed, plus a second hop from a named term's files to their tests.

    Edges touching a stale (superseded or archived) note are dropped - except the
    `supersedes` edge from its successor, kept as history, which `recommend` never walks.
    With a cap on edges, order decides what survives: edges from terms the question
    named, then from remembered notes (curated links to code), then tests of seed
    files, then the rest.
    """
    edges = [
        e
        for e in index.edges_touching(seeds, MIN_EDGE_CONFIDENCE)
        if not {e.src, e.dst} & stale or (e.rel == "supersedes" and e.src not in stale)
    ]
    implementations = [e.dst for e in edges if e.rel == "implemented_in" and e.src in named]
    edges += [e for e in index.edges_touching(implementations, MIN_EDGE_CONFIDENCE) if e.rel == "tested_in"]

    def priority(edge: Edge) -> tuple[int, float]:
        if edge.src in named:
            rank = 0
        elif edge.src.startswith("note:"):
            rank = 1
        elif edge.rel == "tested_in":
            rank = 2
        else:
            rank = 3
        return rank, -edge.confidence

    return sorted(dict.fromkeys(edges), key=priority)[:MAX_EDGES]


def recommend(
    semantic: list[tuple[float, Chunk]], named: set[str], graph: list[Edge], stale: set[str] = frozenset()
) -> list[dict[str, Any]]:
    """What to read, best first. A source scores by its best evidence, not the sum of it: a
    long file with many weak chunks must not outrank the one note that answers the question.
    Something reached through the graph scores GRAPH_DISCOUNT of whatever led there."""
    context: dict[str, dict[str, Any]] = {}

    def add(node: str, score: float, why: str) -> None:
        source = node.removeprefix("file:")
        entry = context.setdefault(source, {"source": source, "score": 0.0, "why": []})
        entry["score"] = round(max(entry["score"], score), 3)
        entry["why"].append(why)

    reached: dict[str, float] = {}
    for score, chunk in semantic:
        node = chunk.source if chunk.source.startswith("note:") else f"file:{chunk.source}"
        reached[node] = max(reached.get(node, 0.0), score)
        lines = f" lines {chunk.start_line}-{chunk.end_line}" if chunk.start_line else ""
        add(node, score, f"semantic match {score:.2f}{lines}")
    top = semantic[0][0] if semantic else 0.7
    for term in named:
        reached[term] = top  # a term the question names is as relevant as the best hit
    for _ in range(2):  # twice: term -> file, then file -> test
        for edge in graph:
            for here, there in ((edge.src, edge.dst), (edge.dst, edge.src)):
                if here in reached and there.startswith(("file:", "note:")) and there not in stale:
                    score = round(reached[here] * GRAPH_DISCOUNT, 3)
                    if score > reached.get(there, 0.0):
                        reached[there] = score
                        add(there, score, f"graph: {edge.src} {edge.rel} {edge.dst}")
    return sorted(context.values(), key=lambda e: e["score"], reverse=True)[:10]


def retrieve_context(
    query: str,
    *,
    index: MemoryIndex,
    embedder: Embedder,
    notes: NoteStore,
    codebase: Path,
    retrievals_dir: Path,
    include_superseded: bool = False,
) -> dict[str, Any]:
    index.require(embedder.name)
    scored = index.search(embedder.embed_query(query), include_superseded=True)
    semantic, hidden = select_semantic(scored, include_superseded)
    stale = (
        set()
        if include_superseded
        else {
            f"note:{n}" for n, status in index.note_statuses().items() if status in ("superseded", "archived")
        }
    )

    entity_hits = match_entities(query, index)
    named = {h["id"] for h in entity_hits}
    seeds = [h["id"] for h in entity_hits]
    for _, chunk in semantic:
        seeds.append(chunk.source if chunk.source.startswith("note:") else f"file:{chunk.source}")
    graph = expand(list(dict.fromkeys(seeds)), named, stale, index)
    recommended = recommend(semantic, named, graph, stale)

    memories = []
    for _, chunk in semantic:
        if chunk.source.startswith("note:"):
            try:
                note = notes.read(chunk.source.removeprefix("note:"))
            except NoteError:
                continue
            memories.append(
                {
                    k: getattr(note, k)
                    for k in ("id", "title", "statement", "rationale", "status", "confidence", "sources")
                }
                | {"superseded_by": note.superseded_by}
            )

    result = {
        "query": query,
        "embedder": embedder.name,
        "semantic_hits": [
            {
                "source": chunk.source,
                "kind": chunk.kind,
                "lines": f"{chunk.start_line}-{chunk.end_line}" if chunk.start_line else None,
                "status": chunk.status if chunk.kind == "note" else None,
                "score": round(score, 3),
                "text": chunk.text.split("\n", 1)[-1][:SNIPPET_CHARS],
            }
            for score, chunk in semantic
        ],
        "entity_hits": entity_hits,
        "graph_expansion": [asdict(e) for e in graph],
        "memories": memories,
        "recommended_context": recommended,
        "gaps": gaps(query, semantic, hidden, entity_hits, graph, recommended, memories, index, codebase)
        + _evidence_gaps(scored, graph, stale),
    }
    result["artifact"] = str(_record(result, retrievals_dir))
    return result


def gaps(
    query: str,
    semantic: list[tuple[float, Chunk]],
    hidden: list[tuple[float, Chunk]],
    entity_hits: list[dict[str, str]],
    graph: list[Edge],
    recommended: list[dict[str, Any]],
    memories: list[dict[str, Any]],
    index: MemoryIndex,
    codebase: Path,
) -> list[str]:
    found = []
    if not any(m["status"] in ("current", "uncertain") for m in memories):
        found.append(
            "No current memory note matched; any rationale must come from source files, docs or Git."
        )
    for _, chunk in hidden:
        found.append(f"Left out {chunk.source} because it is {chunk.status}; ask for history to see it.")
    for memory in memories:
        if memory["status"] == "uncertain":
            found.append(
                f"note:{memory['id']} is marked uncertain - verify it against source before relying on it."
            )
        if memory["status"] == "superseded":
            found.append(f"note:{memory['id']} is superseded by note:{memory['superseded_by']}.")
    if not any(h["id"].startswith("term:") for h in entity_hits):
        found.append(
            "No knowledge-graph term matched the question; relationships come from semantic hits only."
        )
    for term in {h["id"] for h in entity_hits if h["id"].startswith("term:")}:
        files = [e.dst for e in index.edges_touching([term]) if e.rel == "implemented_in" and e.src == term]
        tests = [e for e in index.edges_touching(files) if e.rel == "tested_in"]
        if files and not tests:
            found.append(f"No test file follows the naming convention for any file implementing {term}.")
    for entry in recommended:
        source = entry["source"]
        if source.startswith("note:"):
            continue
        indexed = index.document_sha(source)
        path = codebase / source
        if not path.is_file():
            found.append(f"{source} is referenced but does not exist in the codebase now.")
        elif indexed and hashlib.sha1(path.read_bytes()).hexdigest() != indexed:
            found.append(
                f"{source} changed since it was indexed; read it directly or re-run `librarian index`."
            )
    if HISTORY_QUESTION.search(query):
        found.append(
            "Retrieval does not search Git history; use git_log / git_show / file_history for when and why."
        )
    if not semantic:
        found.append("Nothing in the index matched.")
    return list(dict.fromkeys(found))


def _evidence_gaps(scored: list[tuple[float, Chunk]], graph: list[Edge], stale: set[str]) -> list[str]:
    found = []
    sigmas = strength(scored)
    if sigmas is not None and sigmas < WEAK_EVIDENCE_SIGMAS:
        found.append(
            f"Weak evidence: the best match is only {sigmas:.1f} standard deviations above a typical chunk; "
            "the index may not cover this question - verify in source before relying on any hit."
        )
    for edge in graph:
        if edge.rel == "supersedes" and edge.dst in stale:
            found.append(f"{edge.src} supersedes {edge.dst}; ask with include_superseded for the history.")
    return found


def _record(result: dict[str, Any], retrievals_dir: Path) -> Path:
    retrievals_dir.mkdir(parents=True, exist_ok=True)
    moment = datetime.now(UTC)
    artifact = retrievals_dir / f"{moment:%Y%m%dT%H%M%S%fZ}-{slug(result['query'])[:40]}.json"
    artifact.write_text(json.dumps(result | {"timestamp": moment.isoformat()}, indent=2), encoding="utf-8")
    summary = {
        "timestamp": moment.isoformat(),
        "query": result["query"],
        "artifact": artifact.name,
        "top_context": [e["source"] for e in result["recommended_context"][:5]],
        "gaps": len(result["gaps"]),
    }
    with (retrievals_dir / "retrievals.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(summary) + "\n")
    return artifact
