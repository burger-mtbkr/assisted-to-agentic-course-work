"""The harness's callable catalog, plus its own read-only repo tools."""

from __future__ import annotations

import asyncio
import inspect
import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

MAX_RESULT_CHARS = 30_000


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: Callable
    source: str  # "harness" or "mcp:<server>"


@dataclass(frozen=True)
class ToolOutcome:
    content: str
    is_error: bool


class ToolError(Exception):
    """A tool failed in a way the model should be told about, in plain words."""


def _to_text(value: object) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)


def _cap(text: str) -> str:
    if len(text) <= MAX_RESULT_CHARS:
        return text
    return text[:MAX_RESULT_CHARS] + f"\n[truncated by harness: {len(text)} chars, kept {MAX_RESULT_CHARS}]"


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    async def execute(self, name: str, arguments: dict) -> ToolOutcome:
        tool = self._tools.get(name)
        if tool is None:
            known = ", ".join(sorted(self._tools))
            return ToolOutcome(f"Unknown tool '{name}'. Available tools: {known}", True)
        try:
            if inspect.iscoroutinefunction(tool.handler):
                result = await tool.handler(**arguments)
            else:  # blocking handlers (subprocesses, file reads) must not stall the event loop
                result = await asyncio.to_thread(tool.handler, **arguments)
        except TypeError as exc:
            return ToolOutcome(f"Invalid arguments for {name}: {exc}", True)
        except ToolError as exc:
            return ToolOutcome(str(exc), True)
        except Exception as exc:  # a tool bug must not end the conversation
            return ToolOutcome(f"{name} failed: {type(exc).__name__}: {exc}", True)
        if isinstance(result, ToolOutcome):
            return ToolOutcome(_cap(result.content), result.is_error)
        return ToolOutcome(_cap(_to_text(result)), False)


GIT_TIMEOUT_SECONDS = 30


class RepoTools:
    """Read-only access to the paired repository: confined to its root, and never to
    git-ignored files (config-service/.env holds secrets)."""

    def __init__(self, root: Path):
        self.root = root.resolve()

    def _inside(self, path: str) -> Path:
        target = (self.root / path).resolve()
        if not target.is_relative_to(self.root):
            raise ToolError(f"'{path}' is outside the repository root {self.root}")
        return target

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args], cwd=self.root, capture_output=True, text=True, stdin=subprocess.DEVNULL,
            encoding="utf-8", errors="replace", timeout=GIT_TIMEOUT_SECONDS,
        )

    def read_file(self, path: str, start_line: int = 1, end_line: int = 200) -> str:
        target = self._inside(path)
        if not target.is_file():
            raise ToolError(f"No such file: {path} (paths are relative to {self.root})")
        ignored = self._git("check-ignore", "-q", "--", str(target)).returncode
        if ignored != 1:  # 0 = ignored, anything else = could not verify; refuse both
            raise ToolError(f"Refusing to read {path}: it is git-ignored (local config or secrets) "
                            "or its status could not be checked.")
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        start = max(start_line, 1)
        end = min(end_line, len(lines))
        numbered = [f"{n:>5}  {lines[n - 1]}" for n in range(start, end + 1)]
        header = f"{path} lines {start}-{end} of {len(lines)}"
        return "\n".join([header, *numbered])

    def search_code(self, query: str, max_results: int = 30) -> str:
        """Fixed-string search over tracked files (git grep), case-insensitive."""
        max_results = min(max(int(max_results), 1), 100)
        proc = self._git("grep", "-n", "-I", "-i", "-F", "-e", query)
        if proc.returncode == 1:
            return f"No matches for '{query}'."
        if proc.returncode != 0:
            raise ToolError(f"git grep failed: {proc.stderr.strip()}")
        hits = proc.stdout.splitlines()
        shown = hits[:max_results]
        more = f"\n[{len(hits) - len(shown)} more matches not shown]" if len(hits) > len(shown) else ""
        return "\n".join(shown) + more
