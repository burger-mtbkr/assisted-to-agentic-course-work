"""Saved chats: one JSON file per chat, holding the agent's own conversation state."""

from __future__ import annotations

import json
import re
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

_SESSION_ID = re.compile(r"[0-9a-f]{32}")
TITLE_CHARS = 60


class UnreadableSession(ValueError):
    """A chat file exists but is not one this hub can read."""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def title_from(text: str) -> str:
    """A chat title from its first message: one line, cut at a word near TITLE_CHARS."""
    line = " ".join(text.split())
    if len(line) <= TITLE_CHARS:
        return line
    return (line[:TITLE_CHARS].rsplit(" ", 1)[0] or line[:TITLE_CHARS]) + "..."


class SessionStore:
    """`state` is whatever the chat's agent keeps as its conversation - the PAIR Agent's
    messages array, or a Deep Agent's serialised LangChain messages - so a chat resumes
    exactly where it stopped. The store never interprets it."""

    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        if not _SESSION_ID.fullmatch(session_id):
            raise KeyError(session_id)
        return self.root / f"{session_id}.json"

    def list(self) -> list[dict]:
        summaries = []
        for path in self.root.glob("*.json"):
            try:
                session = json.loads(path.read_text(encoding="utf-8"))
                summaries.append(
                    {key: session[key] for key in ("id", "agent", "title", "created", "updated")}
                )
            except (OSError, ValueError, KeyError, TypeError) as exc:
                print(f"[warning] skipping unreadable chat {path.name}: {exc}", file=sys.stderr)
        return sorted(summaries, key=lambda s: s["updated"], reverse=True)

    def create(self, agent: str, title: str = "", state: list | None = None) -> dict:
        now = _now()
        session = {
            "id": uuid.uuid4().hex,
            "agent": agent,
            "title": title,
            "created": now,
            "updated": now,
            "state": state or [],
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }
        self._write(session)
        return session

    def get(self, session_id: str) -> dict:
        path = self._path(session_id)
        try:
            session = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise KeyError(session_id) from None
        except (OSError, ValueError) as exc:
            raise UnreadableSession(f"{path.name}: {exc}") from exc
        missing = {"id", "agent", "title", "state", "usage"} - set(
            session if isinstance(session, dict) else ()
        )
        if missing:
            raise UnreadableSession(f"{path.name} has no {', '.join(sorted(missing))}")
        return session

    def save(self, session: dict) -> None:
        session["updated"] = _now()
        self._write(session)

    def delete(self, session_id: str) -> None:
        try:
            self._path(session_id).unlink()
        except FileNotFoundError:
            raise KeyError(session_id) from None

    def _write(self, session: dict) -> None:
        path = self._path(session["id"])
        staging = path.with_suffix(".tmp")
        staging.write_text(json.dumps(session, indent=2, ensure_ascii=False), encoding="utf-8")
        staging.replace(path)  # a crash mid-write never leaves a half-written chat
