"""Durable memory: ADR-like Markdown notes that outlive a session.

A note holds what the source does not say - a decision and why - with where it came
from, how sure we are, and whether it is still current. Notes are never deleted: a
correction supersedes the old note, which keeps its text and points at its successor,
so "what did we think before?" stays answerable.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml

STATUSES = ("current", "uncertain", "superseded", "archived")
# Nothing but the user's word behind it: plausible, not established.
USER_ONLY_CONFIDENCE = 0.7
NOTE_ID = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$")
DECISION, RATIONALE = "## Decision", "## Rationale"


class NoteError(ValueError):
    """A note request the store refuses, explained in words the model can act on."""


@dataclass
class MemoryNote:
    id: str
    title: str
    statement: str
    rationale: str
    status: str = "current"
    confidence: float = 0.7
    sources: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    supersedes: list[str] = field(default_factory=list)
    superseded_by: str | None = None
    created: str = ""

    def to_markdown(self) -> str:
        meta = {k: v for k, v in asdict(self).items() if k not in ("statement", "rationale")}
        front = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)
        return f"---\n{front}---\n{DECISION}\n\n{self.statement}\n\n{RATIONALE}\n\n{self.rationale}\n"

    @classmethod
    def from_markdown(cls, text: str) -> MemoryNote:
        _, front, body = text.split("---\n", 2)
        decision, _, rationale = body.partition(RATIONALE)
        return cls(
            **yaml.safe_load(front),
            statement=decision.replace(DECISION, "", 1).strip(),
            rationale=rationale.strip(),
        )

    def embedding_text(self) -> str:
        return f"{self.title}. {self.statement} Rationale: {self.rationale}"


def is_user_source(source: str) -> bool:
    return source.lower().startswith("user")


def provenance(sources: Iterable[str], moment: datetime) -> list[str]:
    """Sources as recorded. A user statement is stamped with today's date by the store,
    never by the model: a model asked for 'user, <date>' will happily invent the date."""
    cleaned = [s.strip() for s in sources if s.strip()] or ["user"]
    stamped = [f"user, {moment:%Y-%m-%d}" if is_user_source(s) else s for s in cleaned]
    return list(dict.fromkeys(stamped))


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60].strip("-") or "note"


class NoteStore:
    def __init__(self, notes_dir: Path):
        self.notes_dir = notes_dir

    def _path(self, note_id: str) -> Path:
        if not NOTE_ID.match(note_id):
            raise NoteError(f"{note_id!r} is not a note id (expected YYYY-MM-DD-some-title).")
        return self.notes_dir / f"{note_id}.md"

    def read(self, note_id: str) -> MemoryNote:
        path = self._path(note_id)
        if not path.is_file():
            raise NoteError(f"No note {note_id!r}. List the notes to see which exist.")
        return MemoryNote.from_markdown(path.read_text(encoding="utf-8"))

    def list(self, status: str | None = None) -> list[MemoryNote]:
        if not self.notes_dir.is_dir():
            return []
        notes = [
            MemoryNote.from_markdown(p.read_text(encoding="utf-8"))
            for p in sorted(self.notes_dir.glob("*.md"))
        ]
        return [n for n in notes if status is None or n.status == status]

    def _write(self, note: MemoryNote) -> None:
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self._path(note.id).write_text(note.to_markdown(), encoding="utf-8")

    def remember(
        self,
        *,
        title: str,
        statement: str,
        rationale: str,
        sources: Iterable[str],
        confidence: float = 0.7,
        entities: Iterable[str] = (),
        supersedes: Iterable[str] = (),
        status: str = "current",
        now: datetime | None = None,
    ) -> MemoryNote:
        """Write a new note; any note it supersedes is marked superseded, not deleted."""
        if not (title.strip() and statement.strip() and rationale.strip()):
            raise NoteError("A note needs a title, a statement and a rationale.")
        if status not in ("current", "uncertain"):
            raise NoteError(
                "A new note is 'current' or 'uncertain'; older notes are superseded by newer ones."
            )
        if not 0.0 <= confidence <= 1.0:
            raise NoteError("confidence is between 0 and 1.")
        replaced = [self.read(note_id) for note_id in supersedes]
        moment = now or datetime.now(UTC)
        sources = provenance(sources, moment)
        if all(is_user_source(s) for s in sources):
            confidence = min(confidence, USER_ONLY_CONFIDENCE)
        base = f"{moment:%Y-%m-%d}-{slug(title)}"
        note_id, n = base, 2
        while self._path(note_id).exists():
            note_id, n = f"{base}-{n}", n + 1
        note = MemoryNote(
            id=note_id,
            title=title.strip(),
            statement=statement.strip(),
            rationale=rationale.strip(),
            status=status,
            confidence=round(float(confidence), 2),
            sources=sources,
            entities=[e.strip() for e in entities if e.strip()],
            supersedes=[old.id for old in replaced],
            created=moment.isoformat(timespec="seconds"),
        )
        self._write(note)
        for old in replaced:
            old.status, old.superseded_by = "superseded", note.id
            self._write(old)
        return note
