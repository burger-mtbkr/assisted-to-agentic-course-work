"""`librarian inspect`: the whole memory state on one screen, for a human reviewer."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from librarian_agent.config import LibrarianConfig
from librarian_agent.notes import NoteStore
from librarian_agent.store import MemoryIndex


def _staleness(index: MemoryIndex, codebase: Path) -> tuple[list[str], list[str]]:
    changed, missing = [], []
    for path, sha in index.documents().items():
        file = codebase / path
        if not file.is_file():
            missing.append(path)
        elif hashlib.sha1(file.read_bytes()).hexdigest() != sha:
            changed.append(path)
    return changed, missing


def report(config: LibrarianConfig, retrievals: int = 5) -> str:
    out = [f"Librarian memory: {config.memory_dir}", ""]

    notes = NoteStore(config.notes_dir).list()
    out.append(f"Notes ({config.notes_dir.name}/): {len(notes)}")
    for note in notes:
        tail = f" -> superseded by {note.superseded_by}" if note.superseded_by else ""
        out.append(f"  [{note.status} {note.confidence:.2f}] {note.id}{tail}")
        out.append(f"      {note.statement[:150]}")
        out.append(f"      sources: {', '.join(note.sources) or 'none'}")
    out.append("")

    index = MemoryIndex(config.db_path)
    stats = index.stats()
    if not stats:
        out.append("Index: none yet - run `librarian index`.")
    else:
        changed, missing = _staleness(index, config.codebase_path)
        out.append(f"Index ({config.db_path.name}): built by {stats['embedder']} at {stats['indexed_at']}")
        out.append(
            f"  documents: {stats['documents']} ({len(changed)} changed since, {len(missing)} missing)"
        )
        for path in [*changed, *missing][:10]:
            out.append(f"    stale: {path}")
        for label, key in (("chunks", "chunks_by_kind"), ("entities", "entities_by_kind")):
            out.append(f"  {label}: " + ", ".join(f"{k} {v}" for k, v in stats[key].items()))
        out.append(
            "  relationships: " + ", ".join(f"{k} {v}" for k, v in stats["relationships_by_type"].items())
        )
    out.append("")

    log = config.retrievals_dir / "retrievals.jsonl"
    records = (
        [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.is_file() else []
    )
    out.append(
        f"Retrievals ({config.retrievals_dir.name}/): {len(records)}, latest {min(retrievals, len(records))}"
    )
    for record in records[-retrievals:]:
        out.append(f"  {record['timestamp'][:19]}  {record['query'][:70]!r}")
        top = ", ".join(record["top_context"][:4])
        out.append(f"      top: {top}  gaps: {record['gaps']}  -> {record['artifact']}")
    out.append("")

    for kind in ("conversations", "traces"):
        files = sorted((config.memory_dir / kind).glob("*.jsonl"))
        latest = f" (latest {files[-1].name})" if files else ""
        out.append(f"{kind.capitalize()}: {len(files)}{latest}")
    return "\n".join(out)
