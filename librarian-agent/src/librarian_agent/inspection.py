"""`librarian inspect`: the whole memory state on one screen, for a human reviewer -
including where memory and its index have drifted apart."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from agent_kit.mount import visible_files

from librarian_agent.config import LibrarianConfig
from librarian_agent.indexer import indexable
from librarian_agent.notes import MemoryNote, NoteStore
from librarian_agent.store import MemoryIndex


def _staleness(index: MemoryIndex, codebase: Path) -> tuple[list[str], list[str], list[str]]:
    """Indexed files changed or missing since the build, and indexable files added since."""
    documents = index.documents()
    changed, missing = [], []
    for path, sha in documents.items():
        file = codebase / path
        if not file.is_file():
            missing.append(path)
        elif hashlib.sha1(file.read_bytes()).hexdigest() != sha:
            changed.append(path)
    added = [p for p in visible_files(codebase) if indexable(p) and p not in documents]
    return changed, missing, added


def _note_drift(notes: list[MemoryNote], index: MemoryIndex) -> list[str]:
    indexed = index.note_statuses()
    drift = [f"not indexed: {n.id}" for n in notes if n.id not in indexed]
    drift += [
        f"status differs: {n.id} is {n.status} in its file, {indexed[n.id]} in the index"
        for n in notes
        if n.id in indexed and indexed[n.id] != n.status
    ]
    return drift


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def report(config: LibrarianConfig, retrievals: int = 5) -> str:
    out = [f"Librarian memory: {config.memory_dir}", ""]

    notes, unreadable = NoteStore(config.notes_dir).scan()
    out.append(f"Notes ({config.notes_dir.name}/): {len(notes)}")
    for note in notes:
        tail = f" -> superseded by {note.superseded_by}" if note.superseded_by else ""
        out.append(f"  [{note.status} {note.confidence:.2f}] {note.id}{tail}")
        out.append(f"      {note.statement[:150]}")
        out.append(f"      sources: {', '.join(note.sources) or 'none'}")
    out += [f"  UNREADABLE: {name}" for name in unreadable]
    out.append("")

    index = MemoryIndex(config.db_path)
    stats = index.stats()
    if not stats:
        out.append("Index: none yet - run `librarian index`.")
    else:
        changed, missing, added = _staleness(index, config.codebase_path)
        out.append(f"Index ({config.db_path.name}): built by {stats['embedder']} at {stats['indexed_at']}")
        out.append(
            f"  documents: {stats['documents']} ({len(changed)} changed since, {len(missing)} missing, "
            f"{len(added)} added)"
        )
        out += [f"    changed: {p}" for p in changed[:10]]
        out += [f"    missing: {p}" for p in missing[:10]]
        out += [f"    added:   {p}" for p in added[:10]]
        for label, key in (("chunks", "chunks_by_kind"), ("entities", "entities_by_kind")):
            out.append(f"  {label}: " + ", ".join(f"{k} {v}" for k, v in stats[key].items()))
        out.append(
            "  relationships: " + ", ".join(f"{k} {v}" for k, v in stats["relationships_by_type"].items())
        )
        drift = _note_drift(notes, index)
        out += [f"  notes {line}" for line in drift] or ["  notes: in step with the index"]
        if added or changed or missing or drift:
            out.append("  -> run `librarian index` to bring the index up to date")
    out.append("")

    log = config.retrievals_dir / "retrievals.jsonl"
    records = _jsonl(log) if log.is_file() else []
    out.append(
        f"Retrievals ({config.retrievals_dir.name}/): {len(records)}, latest {min(retrievals, len(records))}"
    )
    for record in records[-retrievals:]:
        top = ", ".join(record["top_context"][:4])
        out.append(f"  {record['timestamp'][:19]}  {record['query'][:70]!r}")
        out.append(f"      top: {top}  gaps: {record['gaps']}  -> {record['artifact']}")
    out.append("")

    for kind in ("conversations", "traces"):
        files = sorted((config.memory_dir / kind).glob("*.jsonl"))
        out.append(f"{kind.capitalize()}: {len(files)}" + (f" (latest {files[-1].name})" if files else ""))
        if files and kind == "traces":
            events = Counter(e["event"] for e in _jsonl(files[-1]))
            out.append("  latest: " + ", ".join(f"{name} {count}" for name, count in sorted(events.items())))
        if files and kind == "conversations":
            asked = [e["content"] for e in _jsonl(files[-1]) if e["event"] == "user_message"]
            out += [f"  asked: {question[:100]!r}" for question in asked[-3:]]
    return "\n".join(out)


def retrieval_artifact(config: LibrarianConfig, name: str) -> str:
    """One retrieval, readable: what was asked, what came back, and what is missing."""
    artifacts = sorted(config.retrievals_dir.glob("*.json"))
    if not artifacts:
        return "No retrievals yet."
    path = artifacts[-1] if name == "latest" else config.retrievals_dir / Path(name).name
    if not path.is_file():
        return f"No retrieval artifact {name!r} in {config.retrievals_dir}."
    data = json.loads(path.read_text(encoding="utf-8"))
    out = [f"{path.name}", f"query: {data['query']!r} ({data['embedder']})", "", "semantic hits:"]
    out += [
        f"  {h['score']:.3f}  {h['source']}" + (f" {h['lines']}" if h["lines"] else "")
        for h in data["semantic_hits"]
    ]
    out += ["", "entity hits:", *(f"  {e['id']} ({e['matched_by']})" for e in data["entity_hits"])]
    out += ["", "graph:", *(f"  {e['src']} {e['rel']} {e['dst']}" for e in data["graph_expansion"][:15])]
    out += [
        "",
        "recommended:",
        *(f"  {c['score']:.3f}  {c['source']}  <- {c['why'][0]}" for c in data["recommended_context"]),
    ]
    out += ["", "gaps:", *(f"  - {g}" for g in data["gaps"])]
    return "\n".join(out)
