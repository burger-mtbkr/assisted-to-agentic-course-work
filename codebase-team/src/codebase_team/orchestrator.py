"""The workflow: a deterministic pipeline with a human gate, not agents chatting.

    create run -> Doctor.diagnose -> Librarian.retrieve_context -> approval proposed
      (stop: a human approves or narrows the boundary)
    -> Mechanic.patch (only if approved) -> Doctor.verify -> Librarian.remember_repair (optional)

Every specialist call is recorded with the workspace fingerprint before and after, so the
evals can tell which step changed what. A specialist that crashes is a failed step, not a
crashed run, and the original codebase is re-fingerprinted after every step: if it changed,
the run stops.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from agent_kit.mount import canonical_grant
from dotenv import dotenv_values

from codebase_team.artifacts import (
    AgentRequest,
    AgentResult,
    ApprovalRecord,
    Artifact,
    ArtifactError,
    ContextBrief,
    DiagnosisReport,
    VerificationReport,
    read_artifact,
    write_artifact,
)
from codebase_team.port import AgentPort
from codebase_team.trajectory import Trajectory
from codebase_team.workspace import Run, create_run, fingerprint

PROJECT_ROOT = Path(__file__).resolve().parents[2]
A = TypeVar("A", bound=Artifact)


class SourceChanged(Exception):
    """The original codebase changed while the run was in progress."""


def canonical_paths(workspace: Path, paths: list[str]) -> list[str]:
    """Grants as the workspace spells them: an existing file, or an existing directory ending
    in `/`. A grant for something that is not there is a typo, not a permission."""
    root = workspace.resolve()
    grants = []
    for raw in paths:
        rel = canonical_grant(raw).rstrip("/")
        target = Path(os.path.realpath(root / rel))  # the on-disk spelling, case included
        if not target.is_relative_to(root) or target == root:
            raise ValueError(f"Cannot grant {raw!r}: it is not inside the workspace.")
        spelled = target.relative_to(root).as_posix()
        if target.is_file():
            grants.append(spelled)
        elif target.is_dir():
            grants.append(spelled + "/")
        else:
            raise ValueError(f"Cannot grant {raw!r}: no such file or directory in the workspace.")
    return list(dict.fromkeys(grants))


@dataclass(frozen=True)
class TeamConfig:
    source: Path
    runs_dir: Path
    test_command: str
    lint_command: str
    timeout_seconds: int
    model: str
    api_key: str

    @classmethod
    def load(cls, project_root: Path = PROJECT_ROOT) -> TeamConfig:
        settings = {**dotenv_values(project_root / ".env"), **os.environ}

        def get(name: str, default: str) -> str:
            return (settings.get(name) or default).strip()

        def path(name: str, default: str) -> Path:
            value = Path(get(name, default)).expanduser()
            return (value if value.is_absolute() else project_root / value).resolve()

        return cls(
            source=path("TEAM_SOURCE_PATH", "../config-service"),
            runs_dir=path("TEAM_RUNS_DIR", ".codebase-team-runs"),
            test_command=get("TEAM_TEST_COMMAND", "npm run test:api"),
            lint_command=get("TEAM_LINT_COMMAND", "npm run lint:api"),
            timeout_seconds=int(get("TEAM_COMMAND_TIMEOUT", "600")),
            model=get("GEMINI_MODEL", "gemini-flash-latest"),
            api_key=get("GEMINI_API_KEY", ""),
        )


class Team:
    def __init__(
        self, config: TeamConfig, doctor: AgentPort, librarian: AgentPort, mechanics: Mapping[str, AgentPort]
    ):
        self.config = config
        self.doctor = doctor
        self.librarian = librarian
        self.mechanics = mechanics

    @staticmethod
    def trajectory(run: Run) -> Trajectory:
        return Trajectory(run.trajectory_path)

    def _call(
        self, run: Run, agent: AgentPort, request_type: str, instructions: str, **constraints: object
    ) -> AgentResult:
        inputs = {"run": str(run.root), "workspace": str(run.workspace), "artifacts": str(run.artifacts)}
        request = AgentRequest(run.task_id, request_type, instructions, inputs, dict(constraints))
        log = self.trajectory(run)
        log.record(
            "specialist_request", agent=agent.name, request_type=request_type, instructions=instructions
        )
        before = fingerprint(run.workspace)
        try:
            result = agent.handle(request)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            log.record("specialist_error", agent=agent.name, request_type=request_type, error=error)
            result = AgentResult(agent.name, "failed", f"{agent.name} failed: {error}")
        log.record(
            "specialist_result",
            agent=agent.name,
            request_type=request_type,
            status=result.status,
            summary=result.summary,
            artifacts=result.artifacts,
            workspace_changed=fingerprint(run.workspace) != before,
        )
        for artifact in result.artifacts:
            log.record("artifact_written", agent=agent.name, path=artifact)
        meta = run.meta()
        if fingerprint(Path(meta["source"])) != meta["source_fingerprint"]:
            log.record("source_changed", agent=agent.name, request_type=request_type)
            raise SourceChanged(f"the original codebase changed during {agent.name}.{request_type}")
        return result

    def _handoff(self, run: Run, result: AgentResult, kind: type[A]) -> A | None:
        """The artifact a step exists to produce - None, recorded, if the step did not produce
        a valid one (an older file from an earlier attempt does not count)."""
        try:
            if result.status == "failed":
                raise ArtifactError(result.summary)
            return read_artifact(run.artifacts, kind)
        except ArtifactError as exc:
            self.trajectory(run).record("handoff_missing", artifact=kind.__name__, reason=str(exc))
            return None

    # -- steps ------------------------------------------------------------------

    def start(self, scenario: str | None = None) -> Run:
        run = create_run(self.config.source, self.config.runs_dir, scenario)
        self.trajectory(run).record("workflow_start", source=str(self.config.source), scenario=scenario)
        return run

    def diagnose(self, run: Run) -> DiagnosisReport | None:
        result = self._call(
            run, self.doctor, "diagnose", "Run the checks and diagnose the failure. Do not edit anything."
        )
        return self._handoff(run, result, DiagnosisReport)

    def brief(self, run: Run) -> ContextBrief | None:
        result = self._call(
            run,
            self.librarian,
            "retrieve_context",
            "Using the DiagnosisReport, gather what a Mechanic needs for the smallest safe repair.",
        )
        return self._handoff(run, result, ContextBrief)

    def propose(self, run: Run, brief: ContextBrief) -> ApprovalRecord:
        proposal = ApprovalRecord(
            task_id=run.task_id,
            approved=False,
            approved_by="proposal",
            allowed_paths=brief.relevant_source_files,
            allowed_commands=[],  # running the tests runs the Mechanic's code: the human opts in
            rationale="Proposed from the context brief's edit boundary; not approved until a human says so.",
        )
        write_artifact(run.artifacts, proposal)
        self.trajectory(run).record("approval_proposed", allowed_paths=proposal.allowed_paths)
        return proposal

    def approve(
        self,
        run: Run,
        paths: list[str],
        rationale: str,
        commands: list[str],
        approved: bool = True,
        by: str = "human",
    ) -> ApprovalRecord:
        """Record the human decision. It must be made with the brief in hand, and every path
        must name something in the workspace (raises ValueError otherwise)."""
        try:
            read_artifact(run.artifacts, ContextBrief)
        except ArtifactError as exc:
            raise ValueError(f"Nothing to approve yet: {exc}") from exc
        paths = canonical_paths(run.workspace, paths) if approved else paths
        record = ApprovalRecord(run.task_id, approved, by, paths, commands, rationale)
        write_artifact(run.artifacts, record)
        self.trajectory(run).record(
            "approval_recorded",
            approved=approved,
            approved_by=by,
            allowed_paths=paths,
            allowed_commands=commands,
        )
        return record

    def patch(self, run: Run, mechanic: str) -> AgentResult:
        result = self._call(
            run,
            self.mechanics[mechanic],
            "patch",
            "Apply the smallest repair inside the approved paths, then report it as the skill describes.",
        )
        log = self.trajectory(run)
        if result.status == "blocked":
            log.record("patch_blocked", reason=result.summary)
        elif result.status == "ok":
            log.record("patch_applied", files_changed=run.changed_files())
        return result

    def verify(self, run: Run) -> VerificationReport | None:
        result = self._call(run, self.doctor, "verify", "Re-run the checks against the patched workspace.")
        report = self._handoff(run, result, VerificationReport)
        if report:
            self.trajectory(run).record("verification_result", status=report.status, passed=report.passed)
        return report

    def remember(self, run: Run) -> AgentResult:
        return self._call(
            run,
            self.librarian,
            "remember_repair",
            "Remember the verified repair, citing every artifact.",
            scenario=run.meta().get("scenario"),
        )

    def finish(self, run: Run, outcome: str, claim: str) -> str:
        self.trajectory(run).record("workflow_end", outcome=outcome, claim=claim)
        return claim

    # -- the two halves of a run, split at the human gate ---------------------

    def to_gate(self, scenario: str | None = None) -> tuple[Run, str]:
        run = self.start(scenario)
        return run, self.gate(run)

    def gate(self, run: Run) -> str:
        """Diagnose and brief a started run, stopping at the approval gate. Split from
        `start` so a caller can show the run while this, the long part, is under way."""
        try:
            return self._to_gate(run)
        except SourceChanged as exc:
            return self.finish(run, "source_changed", f"Stopped: {exc}.")

    def _to_gate(self, run: Run) -> str:
        diagnosis = self.diagnose(run)
        if diagnosis is None:
            return self.finish(run, "failed", "Stopped: the Doctor produced no diagnosis.")
        if diagnosis.status == "healthy":
            return self.finish(run, "healthy", "Healthy: every check passed, nothing to repair.")
        if diagnosis.status == "inconclusive":
            return self.finish(
                run, "inconclusive", f"Stopped: the diagnosis is inconclusive. {diagnosis.observed_error}"
            )
        brief = self.brief(run)
        if brief is None:
            return self.finish(run, "failed", "Stopped: the Librarian produced no context brief.")
        proposal = self.propose(run, brief)
        self.trajectory(run).record("awaiting_approval")
        return f"Waiting for approval. Proposed boundary: {', '.join(proposal.allowed_paths) or '(none)'}"

    def past_gate(self, run: Run, mechanic: str, remember: bool = False) -> str:
        try:
            return self._past_gate(run, mechanic, remember)
        except SourceChanged as exc:
            return self.finish(run, "source_changed", f"Not repaired: stopped, {exc}.")

    def _past_gate(self, run: Run, mechanic: str, remember: bool) -> str:
        patched = self.patch(run, mechanic)
        if patched.status == "blocked":
            return self.finish(run, "blocked", f"Not repaired: {patched.summary}")
        if patched.status != "ok":
            return self.finish(run, "patch_failed", f"Not repaired: {patched.summary}")
        report = self.verify(run)
        if report is None:
            return self.finish(run, "inconclusive", "Not repaired: the Doctor produced no verification.")
        if report.status != "verified":
            return self.finish(
                run, report.status, f"Not repaired: verification {report.status}. {report.recommendation}"
            )
        if remember:
            self.remember(run)
        return self.finish(run, "verified", f"Repaired and verified. {report.recommendation}")
