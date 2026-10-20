"""Per-session artifacts a human can read after a run: conversation and trace, as JSONL.

conversations/conversation_<id>.jsonl - what was said and done: user and assistant
    messages, tool calls with arguments, tool results, skills read.
traces/trace_<id>.jsonl - how long it took: one record per conversation turn, model
    call, tool call and final response, each with duration_ms and status.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

OUTPUT_LIMIT = 6000
TRUNCATION_MARKER = "\n... [output truncated: kept the first and last parts] ...\n"


def compact(text: str, limit: int = OUTPUT_LIMIT) -> str:
    """Keep the head and the tail of long output: test runners print the failure summary last."""
    text = text.strip()
    if len(text) <= limit:
        return text
    keep = limit - len(TRUNCATION_MARKER)
    head = keep // 2
    return text[:head] + TRUNCATION_MARKER + text[-(keep - head) :]


def new_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]


class RunRecorder:
    def __init__(self, runs_dir: Path, session_id: str | None = None):
        self.session_id = session_id or new_id()
        self.conversation_path = runs_dir / "conversations" / f"conversation_{self.session_id}.jsonl"
        self.trace_path = runs_dir / "traces" / f"trace_{self.session_id}.jsonl"
        self.conversation_path.parent.mkdir(parents=True, exist_ok=True)
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)

    def conversation(self, event: str, **fields: Any) -> None:
        self._append(self.conversation_path, {"conversation_id": self.session_id, "event": event, **fields})

    def trace(self, event: str, trace_id: str, **fields: Any) -> None:
        self._append(
            self.trace_path,
            {"conversation_id": self.session_id, "trace_id": trace_id, "event": event, **fields},
        )

    @staticmethod
    def _append(path: Path, record: dict[str, Any]) -> None:
        line = json.dumps(
            {"timestamp": datetime.now(UTC).isoformat(), **record}, ensure_ascii=False, default=str
        )
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
