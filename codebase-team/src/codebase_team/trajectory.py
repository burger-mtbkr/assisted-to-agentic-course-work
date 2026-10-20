"""The run's event log: what each specialist was asked, what it returned, what was written,
and every human decision - one JSON line each, in order."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class Trajectory:
    def __init__(self, path: Path):
        self.path = path

    def events(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        return [
            json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]

    def record(self, event: str, **fields: Any) -> dict[str, Any]:
        entry = {
            "seq": len(self.events()) + 1,
            "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "event": event,
            **fields,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        return entry
