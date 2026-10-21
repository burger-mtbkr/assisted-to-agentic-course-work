"""One run = one isolated copy of the codebase, with its own git baseline and artifacts.

The copy holds only git-visible files (no `.env`, no `node_modules`, no build output),
committed as a baseline so that "what did the Mechanic change?" is `git diff`. The
original is fingerprinted at creation so evals can prove it was never touched.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agent_kit.mount import ALWAYS_HIDDEN_DIRS, visible_files

from codebase_team import scenarios

GIT_IDENTITY = ["-c", "user.email=codebase-team@localhost", "-c", "user.name=codebase-team"]


def git(cwd: Path, *args: str, index: Path | None = None) -> str:
    """Run git in `cwd`; with `index`, against that index file instead of the repository's."""
    env = {**os.environ, "GIT_INDEX_FILE": str(index)} if index else None
    proc = subprocess.run(
        ["git", *GIT_IDENTITY, "-c", "core.autocrlf=false", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {args[0]} failed in {cwd}: {proc.stderr.strip()}")
    return proc.stdout


def fingerprint(root: Path) -> str:
    """One hash over every git-visible file's path and bytes."""
    digest = hashlib.sha256()
    for name in visible_files(root):
        digest.update(name.encode("utf-8") + b"\0" + hashlib.sha256((root / name).read_bytes()).digest())
    return digest.hexdigest()


@dataclass(frozen=True)
class Run:
    task_id: str
    root: Path

    @property
    def workspace(self) -> Path:
        return self.root / "workspace"

    @property
    def artifacts(self) -> Path:
        return self.root / "artifacts"

    @property
    def trajectory_path(self) -> Path:
        return self.root / "trajectory.jsonl"

    @property
    def mechanic_dir(self) -> Path:
        return self.root / "mechanic"

    def meta(self) -> dict[str, Any]:
        return json.loads((self.root / "run.json").read_text(encoding="utf-8"))

    @contextmanager
    def _scratch_index(self) -> Iterator[Path]:
        """A throwaway copy of the workspace's git index: reading the run (diff, inspect)
        must not change it."""
        with tempfile.TemporaryDirectory() as scratch:
            index = Path(scratch) / "index"
            shutil.copy2(self.workspace / ".git" / "index", index)
            yield index

    def changed_files(self) -> list[str]:
        """Workspace paths that differ from the baseline: modified, new, deleted - and new
        files git ignores, which no diff would show (build and dependency output aside)."""
        with self._scratch_index() as index:
            out = git(
                self.workspace,
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                "--ignored=matching",
                index=index,
            )
        changed = []
        for entry in filter(None, out.split("\0")):
            path = entry[3:].rstrip("/")
            if entry.startswith("!!") and ALWAYS_HIDDEN_DIRS.intersection(path.split("/")):
                continue
            changed.append(path)
        return sorted(changed)

    def diff(self, *options: str) -> str:
        """The change against the baseline commit, new files included, deletions too."""
        with self._scratch_index() as index:
            git(self.workspace, "add", "--intent-to-add", ".", index=index)
            return git(self.workspace, "diff", *options, "HEAD", index=index)

    def diff_stat(self) -> str:
        return self.diff("--stat").strip()

    def revert(self, paths: list[str]) -> None:
        """Put paths back as the baseline commit had them: restore what it had, delete what
        it did not."""
        in_baseline = set(git(self.workspace, "ls-tree", "-r", "-z", "--name-only", "HEAD").split("\0"))
        for path in paths:
            if path in in_baseline:
                git(self.workspace, "checkout", "HEAD", "--", path)
            else:
                (self.workspace / path).unlink(missing_ok=True)
                git(self.workspace, "rm", "--cached", "--quiet", "--ignore-unmatch", "--", path)


def new_task_id() -> str:
    return f"task-{datetime.now(UTC):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:4]}"


def create_run(source: Path, runs_dir: Path, scenario: str | None = None) -> Run:
    task_id = new_task_id()
    run = Run(task_id, runs_dir.resolve() / task_id)
    run.workspace.mkdir(parents=True)
    run.artifacts.mkdir()
    for name in visible_files(source):
        target = run.workspace / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, target)
    applied = scenarios.apply(run.workspace, scenario) if scenario else None
    git(run.workspace, "init", "-q")
    git(run.workspace, "add", "--all")
    git(run.workspace, "commit", "-q", "-m", "baseline")
    try:
        source_head = git(source, "rev-parse", "HEAD").strip()
    except RuntimeError:
        source_head = None
    meta = {
        "task_id": run.task_id,
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": str(source),
        "source_head": source_head,
        "source_fingerprint": fingerprint(source),
        "scenario": applied.name if applied else None,
        "scenario_description": applied.description if applied else None,
    }
    (run.root / "run.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return run


def load_run(runs_dir: Path, task_id: str) -> Run:
    run = Run(task_id, runs_dir.resolve() / task_id)
    if not (run.root / "run.json").is_file():
        raise FileNotFoundError(f"No run {task_id!r} in {runs_dir}")
    return run
