"""Episodic memory: what happened, from Git. Read-only, and scoped to the codebase directory.

`config-service` moved to the repo root in a reorganisation, so directory-level logs
start there; `file_history` follows renames back past it.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

from agent_kit.recording import compact

COMMIT = re.compile(r"^[0-9a-fA-F]{4,40}$")
FIELD, RECORD = "\x1f", "\x1e"
LOG_FORMAT = f"--format=%h{FIELD}%ad{FIELD}%an{FIELD}%s{RECORD}"
GIT_TIMEOUT_SECONDS = 30
DIFF_CHARS = 6000


class HistoryError(ValueError):
    """A history request the tools refuse or Git cannot answer."""


class GitHistory:
    def __init__(self, codebase: Path):
        self.codebase = codebase

    def _git(self, *args: str) -> str:
        proc = subprocess.run(
            ["git", *args],
            cwd=self.codebase,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_TIMEOUT_SECONDS,
        )
        if proc.returncode != 0:
            raise HistoryError(proc.stderr.strip() or f"git {args[0]} failed")
        return proc.stdout

    @staticmethod
    def _pathspec(path: str) -> str:
        """A codebase-relative pathspec. `/codebase/x` (the mount's form) and `/x` both mean `x`."""
        cleaned = path.replace("\\", "/").strip()
        cleaned = cleaned.removeprefix("/codebase/").strip("/") or "."
        pure = PurePosixPath(cleaned)
        if (
            pure.is_absolute()
            or ".." in pure.parts
            or re.match(r"^[A-Za-z]:", cleaned)
            or cleaned.startswith("-")
        ):
            raise HistoryError(f"{path!r} is not a path inside the codebase.")
        return cleaned

    def _commits(self, output: str) -> list[dict[str, str]]:
        commits = []
        for record in filter(None, (r.strip() for r in output.split(RECORD))):
            short, date, author, subject = record.split(FIELD)
            commits.append({"commit": short, "date": date, "author": author, "subject": subject})
        return commits

    def log(self, path: str = "", limit: int = 15) -> dict[str, Any]:
        """Recent commits touching the codebase, or one path in it, newest first."""
        scope = self._pathspec(path)
        limit = min(max(int(limit), 1), 50)
        output = self._git("log", f"-n{limit}", "--date=short", LOG_FORMAT, "--", scope)
        return {"scope": scope, "commits": self._commits(output)}

    def file_history(self, path: str, limit: int = 20) -> dict[str, Any]:
        """Commits that touched one file, following renames."""
        scope = self._pathspec(path)
        limit = min(max(int(limit), 1), 50)
        output = self._git("log", "--follow", f"-n{limit}", "--date=short", LOG_FORMAT, "--", scope)
        return {"path": scope, "commits": self._commits(output)}

    def show(self, commit: str) -> dict[str, Any]:
        """One commit's message, the codebase files it changed, and its codebase diff (compacted)."""
        if not COMMIT.match(commit.strip()):
            raise HistoryError(f"{commit!r} is not a commit hash.")
        sha = commit.strip()
        header = self._git("show", "-s", "--date=short", f"--format=%h{FIELD}%ad{FIELD}%an{FIELD}%B", sha)
        short, date, author, message = header.split(FIELD, 3)
        files = self._git("show", "--format=", "--stat=120", sha, "--", ".").strip()
        diff = self._git("show", "--format=", "--patch", sha, "--", ".")
        return {
            "commit": short.strip(),
            "date": date,
            "author": author,
            "message": message.strip(),
            "files_in_codebase": files or "(this commit changed nothing inside the codebase)",
            "diff": compact(diff, DIFF_CHARS),
        }
