"""Subprocess wrapper around the knowledge-graph CLI.

Knows nothing about MCP: it turns `uv run knowledge-graph ...` into parsed
JSON or a `KgServiceError` carrying a reason, a detail and a fix the agent
can relay to the user.
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

IMPORT_HINT = (
    "uv run knowledge-graph import --knowledge-dir <repo>/config-service/knowledge "
    "--db <repo>/config-service/knowledge/knowledge.db (run inside KG_PROJECT_DIR)"
)


class KgServiceError(Exception):
    """The knowledge graph could not answer - as opposed to answering not_found."""

    def __init__(self, reason: str, detail: str, fix: str):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail
        self.fix = fix

    def to_payload(self) -> dict:
        return {
            "error": "service_error",
            "reason": self.reason,
            "detail": self.detail,
            "fix": self.fix,
        }


@dataclass(frozen=True)
class KgSettings:
    project_dir: Path | None
    db: Path | None
    timeout_seconds: float

    @classmethod
    def from_env(cls) -> KgSettings:
        project_dir = os.environ.get("KG_PROJECT_DIR")
        db = os.environ.get("KG_DB")
        return cls(
            project_dir=Path(project_dir).resolve() if project_dir else None,
            db=Path(db).resolve() if db else None,
            timeout_seconds=float(os.environ.get("KG_TIMEOUT_SECONDS", "60")),
        )


@dataclass(frozen=True)
class CliResult:
    returncode: int
    stdout: str
    stderr: str


Runner = Callable[[KgSettings, tuple[str, ...]], Awaitable[CliResult]]


async def _spawn(settings: KgSettings, args: tuple[str, ...]) -> CliResult:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    try:
        proc = await asyncio.create_subprocess_exec(
            "uv", "run", "--quiet", "knowledge-graph", *args,
            cwd=settings.project_dir,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise KgServiceError(
            "backend_unreachable",
            f"could not start the knowledge-graph CLI: {exc}",
            "Install uv and make sure it is on PATH for the process running this server.",
        ) from exc
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), settings.timeout_seconds)
    except TimeoutError as exc:
        proc.kill()
        await proc.wait()
        raise KgServiceError(
            "timeout",
            f"knowledge-graph {' '.join(args)} did not finish in {settings.timeout_seconds:g}s",
            "Retry once; the first run may be syncing the CLI's environment. "
            "Raise KG_TIMEOUT_SECONDS if it keeps happening.",
        ) from exc
    return CliResult(
        proc.returncode,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )


def _preflight(settings: KgSettings) -> None:
    if settings.project_dir is None:
        raise KgServiceError(
            "not_configured",
            "KG_PROJECT_DIR is not set",
            "Set KG_PROJECT_DIR to the knowledge-graph CLI project directory in the MCP "
            "server registration (.mcp.json or mcp.json).",
        )
    if not settings.project_dir.is_dir():
        raise KgServiceError(
            "backend_unreachable",
            f"KG_PROJECT_DIR does not exist: {settings.project_dir}",
            "Point KG_PROJECT_DIR at the knowledge-graph CLI project. It ships in the "
            "Module 5 curriculum zip (modules/assisted-to-agentic-module-5/examples/"
            "knowledge-graph), which is git-ignored - extract the zip on a fresh clone.",
        )
    if settings.db is not None and not settings.db.is_file():
        raise KgServiceError(
            "knowledge_db_missing",
            f"knowledge database not found: {settings.db}",
            f"Build it from the YAML first: {IMPORT_HINT}",
        )


def _tail(text: str, lines: int = 5) -> str:
    return "\n".join(text.strip().splitlines()[-lines:])


async def run_cli(settings: KgSettings, *args: str, runner: Runner = _spawn) -> CliResult:
    """Run one CLI command after checking the configuration is usable."""
    _preflight(settings)
    return await runner(settings, args)


def _db_args(settings: KgSettings) -> tuple[str, ...]:
    return ("--db", str(settings.db)) if settings.db else ()


async def query_json(
    settings: KgSettings, command: str, *positional: str, runner: Runner = _spawn
) -> dict | list:
    """Run a JSON-emitting command. Options go first and positionals after `--`,
    so a term like `--help` is looked up rather than parsed as a flag."""
    args = (command, "--format", "json", *_db_args(settings))
    if positional:
        args = (*args, "--", *positional)
    result = await run_cli(settings, *args, runner=runner)

    if result.returncode not in (0, 1):
        raise KgServiceError(
            "cli_failed",
            f"knowledge-graph {command} exited {result.returncode}: "
            f"{_tail(result.stderr or result.stdout)}",
            "Run the same command by hand inside KG_PROJECT_DIR to see the full error.",
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise KgServiceError(
            "malformed_output",
            f"knowledge-graph {command} did not return JSON: {result.stdout[:200]!r}",
            "Check that KG_PROJECT_DIR points at a compatible knowledge-graph CLI version.",
        ) from exc
    is_not_found = isinstance(payload, dict) and payload.get("error") == "not_found"
    if result.returncode == 1 and not is_not_found:
        raise KgServiceError(
            "cli_failed",
            f"knowledge-graph {command} exited 1: {_tail(result.stderr or result.stdout)}",
            "Run the same command by hand inside KG_PROJECT_DIR to see the full error.",
        )
    return payload


async def validate(settings: KgSettings, runner: Runner = _spawn) -> dict:
    """`validate` has no --format: exit 0 is valid, exit 1 lists issues on stdout."""
    result = await run_cli(settings, "validate", *_db_args(settings), runner=runner)
    if result.returncode == 0:
        return {"valid": True, "issues": []}
    if result.returncode == 1:
        return {"valid": False, "issues": [line for line in result.stdout.splitlines() if line]}
    raise KgServiceError(
        "cli_failed",
        f"knowledge-graph validate exited {result.returncode}: "
        f"{_tail(result.stderr or result.stdout)}",
        "Run `uv run knowledge-graph validate` by hand inside KG_PROJECT_DIR.",
    )
