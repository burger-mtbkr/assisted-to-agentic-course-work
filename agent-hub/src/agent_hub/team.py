"""The Codebase Team (Module 9) as runs the browser can start, watch, approve and continue.

A run's progress is its own trajectory file, which the team writes as it goes, so the
browser polls a run rather than holding a stream open for minutes. The two halves of a
run - diagnose and brief, then patch and verify - run in a worker thread, one team step
at a time: steps share the service's test run and the free-tier quota.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from dataclasses import asdict, replace
from typing import Any

from codebase_team.artifacts import (
    ApprovalRecord,
    ArtifactError,
    ContextBrief,
    DiagnosisReport,
    PatchSummary,
    VerificationReport,
    read_artifact,
)
from codebase_team.evals import evaluate
from codebase_team.mechanic import TESTS_COMMAND
from codebase_team.orchestrator import Team, TeamConfig
from codebase_team.scenarios import SCENARIOS
from codebase_team.trajectory import Trajectory
from codebase_team.workspace import Run, load_run

from agent_hub.agents import PROFILES, models_for

_TASK_ID = re.compile(r"task-\d{8}-\d{6}-[0-9a-f]{4}")
ARTIFACTS = {
    "diagnosis": DiagnosisReport,
    "brief": ContextBrief,
    "approval": ApprovalRecord,
    "patch": PatchSummary,
    "verification": VerificationReport,
}
DIFF_CHARS = 200_000


class RunBusy(Exception):
    """A step of this run is already under way."""


def run_state(events: list[dict[str, Any]], running: bool) -> dict[str, Any]:
    """Where a run stands, from its trajectory: running, awaiting_approval, approved,
    rejected, finished (with the outcome and the team's claim), or interrupted - a run whose
    step was under way when the hub stopped."""
    names = [e["event"] for e in events]
    if running:
        open_requests = [e for e in events if e["event"] == "specialist_request"]
        done = sum(e["event"] == "specialist_result" for e in events)
        step = open_requests[-1] if len(open_requests) > done else None
        return {
            "state": "running",
            "step": step and {"agent": step["agent"], "request_type": step["request_type"]},
        }
    if "workflow_end" in names:
        end = next(e for e in reversed(events) if e["event"] == "workflow_end")
        return {"state": "finished", "outcome": end["outcome"], "claim": end["claim"]}
    if "approval_recorded" in names:
        decision = next(e for e in reversed(events) if e["event"] == "approval_recorded")
        return {"state": "approved" if decision["approved"] else "rejected"}
    if "awaiting_approval" in names:
        return {"state": "awaiting_approval"}
    return {"state": "interrupted"}


class TeamRuns:
    profile = PROFILES["team"]

    def __init__(self, config: TeamConfig, build_team: Callable[[TeamConfig], Team]):
        self.config = config
        self.build_team = build_team
        self.team = build_team(config)
        self.models = models_for(config.model)
        self._running: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    @property
    def model(self) -> str:
        """The Mechanic's model: the Doctor's and Librarian's team steps call no model."""
        return self.config.model

    def set_model(self, model: str) -> None:
        self.config = replace(self.config, model=model)
        self.team = self.build_team(self.config)  # a step already under way keeps the team it started with

    def describe(self) -> dict:
        return {
            "scenarios": [{"name": s.name, "description": s.description} for s in SCENARIOS.values()],
            "tests_command": TESTS_COMMAND,
        }

    def _load(self, task_id: str) -> Run:
        if not _TASK_ID.fullmatch(task_id):
            raise FileNotFoundError(task_id)
        return load_run(self.config.runs_dir, task_id)

    def _summary(self, run: Run, events: list[dict]) -> dict:
        meta = run.meta()
        return {
            "task_id": run.task_id,
            "created": meta["created"],
            "scenario": meta["scenario"],
            "scenario_description": meta["scenario_description"],
            **run_state(events, run.task_id in self._running),
        }

    def list(self) -> list[dict]:
        runs = []
        for path in sorted(self.config.runs_dir.glob("task-*"), reverse=True):
            try:
                run = self._load(path.name)
                runs.append(self._summary(run, Trajectory(run.trajectory_path).events()))
            except (FileNotFoundError, ValueError, KeyError):
                continue  # a folder that is not a run, or a run still being created
        return runs

    def detail(self, task_id: str) -> dict:
        run = self._load(task_id)
        events = Trajectory(run.trajectory_path).events()
        summary = self._summary(run, events)
        artifacts = {}
        for name, kind in ARTIFACTS.items():
            try:
                artifacts[name] = asdict(read_artifact(run.artifacts, kind))
            except ArtifactError:
                artifacts[name] = None
        diff = run.diff() if summary["state"] != "running" else ""
        evals = []
        if summary["state"] == "finished":
            evals = [asdict(result) for result in evaluate(run)]
        return {
            **summary,
            "source": run.meta()["source"],
            "workspace": str(run.workspace),
            "timeline": events,
            "artifacts": artifacts,
            "changed_files": run.changed_files() if summary["state"] != "running" else [],
            "diff": diff if len(diff) <= DIFF_CHARS else diff[:DIFF_CHARS] + "\n[diff truncated by the hub]",
            "evals": evals,
        }

    def _background(self, run: Run, step: Callable[[], str]) -> None:
        async def go() -> None:
            async with self._lock:
                try:
                    await asyncio.to_thread(step)
                except Exception as exc:  # the team records its own failures; this is anything else
                    Trajectory(run.trajectory_path).record(
                        "workflow_end", outcome="hub_error", claim=f"Stopped: {type(exc).__name__}: {exc}"
                    )

        task = asyncio.create_task(go())
        self._running[run.task_id] = task
        task.add_done_callback(lambda _: self._running.pop(run.task_id, None))

    async def start(self, scenario: str | None) -> dict:
        if scenario is not None and scenario not in SCENARIOS:
            raise ValueError(f"Unknown scenario {scenario!r}; known: {', '.join(SCENARIOS)}")
        run = await asyncio.to_thread(self.team.start, scenario)
        self._background(run, lambda: self.team.gate(run))
        return self._summary(run, Trajectory(run.trajectory_path).events())

    async def approve(
        self, task_id: str, paths: list[str], rationale: str, allow_tests: bool, approved: bool
    ) -> dict:
        run = self._load(task_id)
        state = self._summary(run, Trajectory(run.trajectory_path).events())["state"]
        if state not in ("awaiting_approval", "approved", "rejected"):
            raise ValueError(f"This run is {state.replace('_', ' ')}; there is nothing to approve.")
        if approved and not paths:
            raise ValueError("Approve at least one path, or reject the proposal.")
        if not rationale.strip():
            raise ValueError("Say why: the rationale is part of the record.")
        commands = [TESTS_COMMAND] if allow_tests else []
        await asyncio.to_thread(self.team.approve, run, paths, rationale.strip(), commands, approved)
        return self.detail(task_id)

    async def proceed(self, task_id: str, remember: bool) -> dict:
        run = self._load(task_id)
        state = self._summary(run, Trajectory(run.trajectory_path).events())["state"]
        if state == "running":
            raise RunBusy("This run is already working.")
        if state not in ("approved", "rejected"):
            raise ValueError("Record a decision on the proposal before continuing.")
        self._background(run, lambda: self.team.past_gate(run, "agent", remember))
        return self.detail(task_id)
