"""The Mechanic: the one specialist that edits, and only inside the human's approval.

Two Mechanics sit behind the same port: a live agent (Deep Agents + Gemini through
agent-kit) and a human-assisted one. Both pass the same gate first, and both end in the
same `finish_patch`, which measures what actually changed in the workspace, reverts
anything outside the approved paths, and writes the PatchSummary.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from agent_kit.harness import Session, assemble
from agent_kit.mount import GrantedWriteBackend, normalize
from agent_kit.recording import RunRecorder, compact
from deepagents import FilesystemPermission
from deepagents.backends import FilesystemBackend
from doctor_agent.tools import DiagnosticTools
from langchain_core.language_models import BaseChatModel

from codebase_team.artifacts import (
    AgentRequest,
    AgentResult,
    ApprovalRecord,
    ArtifactError,
    ContextBrief,
    DiagnosisReport,
    Evidence,
    PatchSummary,
    read_artifact,
    write_artifact,
)
from codebase_team.workspace import Run

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"
TESTS_COMMAND = "service tests"
EXCLUDED_TOOLS = frozenset({"delete", "execute", "write_todos", "task"})

MECHANIC_PROMPT = """You are the Mechanic, the repair specialist on a codebase team.

The Doctor has diagnosed a failure and the Librarian has gathered context. A human has
approved a repair boundary. Your job is the smallest change, inside that boundary, that
makes the failing check pass for the right reason. Follow the repair-issue skill under
/skills/.

The codebase is mounted at /workspace/ (a disposable copy). You can read anything git
tracks there; you can write only the approved paths - any other write is refused. You do
not commit, you do not touch tests the approval does not name, and you never claim a fix
works unless a check you ran shows it.
"""


class Blocked(Exception):
    """The approval gate is closed."""


def approval_gate(artifacts: Path) -> ApprovalRecord:
    """The approval, if there is a valid one that says yes. Fails closed."""
    try:
        approval = read_artifact(artifacts, ApprovalRecord)
    except ArtifactError as exc:
        raise Blocked(f"no usable approval: {exc}") from exc
    if not approval.approved:
        raise Blocked(f"approval is not granted ({approval.approved_by}: {approval.rationale})")
    return approval


def allowed(path: str, approval: ApprovalRecord) -> bool:
    for grant in approval.allowed_paths:
        rel = normalize(grant)
        if path == rel or (grant.endswith("/") and path.startswith(rel + "/")):
            return True
    return False


def parse_report(text: str) -> dict[str, Any]:
    """The JSON block the repair-issue skill asks for; plain text if the model skipped it."""
    blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S) or re.findall(
        r"(\{[^{}]*\"intent\".*?\})", text, re.S
    )
    for block in reversed(blocks):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        if isinstance(data, dict) and data.get("intent"):
            risks = data.get("risks") or []
            return {
                "intent": str(data["intent"]),
                "rationale": str(data.get("rationale", "")),
                "risks": [str(r) for r in (risks if isinstance(risks, list) else [risks])],
            }
    first = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return {"intent": first[:300] or "(no summary given)", "rationale": text[:600], "risks": []}


def finish_patch(
    task_id: str, run: Run, approval: ApprovalRecord, mode: str, report: dict[str, Any]
) -> AgentResult:
    """Measure the change, revert what is out of bounds, and write the PatchSummary."""
    changed = run.changed_files()
    outside = [path for path in changed if not allowed(path, approval)]
    risks = list(report.get("risks", []))
    if outside:
        run.revert(outside)
        risks.append(f"Reverted edits outside the approved paths: {', '.join(outside)}")
    kept = [path for path in changed if path not in outside]
    if not kept:
        summary = PatchSummary(
            task_id=task_id,
            mode="no-change",
            intent=report["intent"],
            files_changed=[],
            diff_summary="",
            rationale=report["rationale"],
            risks=risks,
            verification_request="",
            evidence=[],
        )
        path = write_artifact(run.artifacts, summary)
        return AgentResult(
            "Mechanic",
            "failed",
            f"No change made inside the approved paths. {report['intent']}",
            [str(path)],
            next_actions=["Human: re-scope the approval or repair by hand."],
        )
    diff = run.diff()
    summary = PatchSummary(
        task_id=task_id,
        mode=mode,
        intent=report["intent"],
        files_changed=kept,
        diff_summary=run.diff_stat(),
        rationale=report["rationale"],
        risks=risks,
        verification_request=(
            "Run the service tests and lint; the test that failed in the diagnosis must pass, and nothing "
            "else may newly fail."
        ),
        evidence=[Evidence("workspace git diff", "diff", compact(diff, 3000))],
    )
    path = write_artifact(run.artifacts, summary)
    return AgentResult(
        "Mechanic",
        "ok",
        f"Changed {', '.join(kept)}: {report['intent']}",
        [str(path)],
        summary.evidence,
        0.7,
        ["Doctor: verify the patch."],
    )


def pick(artifact: object, *keys: str) -> dict[str, Any]:
    return {key: getattr(artifact, key) for key in keys}


def _handoffs(artifacts: Path) -> str:
    """The three handoffs, trimmed to what a repair needs - not the whole run's history."""
    diagnosis = read_artifact(artifacts, DiagnosisReport)
    brief = read_artifact(artifacts, ContextBrief)
    approval = read_artifact(artifacts, ApprovalRecord)
    return json.dumps(
        {
            "diagnosis": pick(
                diagnosis,
                "failing_tests",
                "observed_error",
                "relevant_files",
                "suspected_cause",
                "uncertainty",
            )
            | {"evidence": [asdict(e) for e in diagnosis.evidence if e.kind in ("test", "source")]},
            "context_brief": pick(brief, "facts", "suggested_constraints", "gaps", "relevant_tests"),
            "approval": pick(approval, "allowed_paths", "allowed_commands", "rationale"),
        },
        indent=1,
    )


class AgentMechanic:
    """A live coding agent behind the port: Deep Agents, Gemini, a write grant per approved path."""

    name = "Mechanic"
    mode = "live-agent"

    def __init__(
        self, model: Callable[[], BaseChatModel], test_command: str, lint_command: str, timeout_seconds: int
    ):
        self.model = model
        self.test_command = test_command
        self.lint_command = lint_command
        self.timeout_seconds = timeout_seconds
        self.session: Session | None = None

    def handle(self, request: AgentRequest) -> AgentResult:
        run = Run(request.task_id, Path(request.inputs["run"]))
        try:
            approval = approval_gate(run.artifacts)
        except Blocked as exc:
            return AgentResult(self.name, "blocked", f"Refused to patch: {exc}")
        checks = DiagnosticTools(run.workspace, self.test_command, self.lint_command, self.timeout_seconds)
        tools = [t for t in checks.as_langchain_tools() if t.name == "run_tests"]
        graph = assemble(
            self.model(),
            system_prompt=MECHANIC_PROMPT,
            tools=tools if TESTS_COMMAND in approval.allowed_commands else [],
            routes={
                "/workspace/": GrantedWriteBackend(run.workspace, approval.allowed_paths),
                "/skills/": FilesystemBackend(SKILLS_DIR, virtual_mode=True),
            },
            excluded_tools=EXCLUDED_TOOLS,
            permissions=[
                FilesystemPermission(
                    operations=["write"],
                    paths=[
                        f"/workspace/{normalize(p)}" + ("/**" if p.endswith("/") else "")
                        for p in approval.allowed_paths
                    ],
                ),
                FilesystemPermission(operations=["write"], paths=["/**"], mode="deny"),
            ],
        )
        self.session = Session(graph, RunRecorder(run.mechanic_dir))
        text = self.session.ask(
            "Repair this failure. The handoffs:\n\n"
            + _handoffs(run.artifacts)
            + "\n\n"
            + request.instructions
        )
        return finish_patch(request.task_id, run, approval, self.mode, parse_report(text))


class HumanMechanic:
    """The human-assisted Mechanic: same gate, same boundary check, a person at the keyboard."""

    name = "Mechanic"
    mode = "human-assisted"

    def __init__(self, ask: Callable[[str], str] = input):
        self.ask = ask

    def handle(self, request: AgentRequest) -> AgentResult:
        run = Run(request.task_id, Path(request.inputs["run"]))
        try:
            approval = approval_gate(run.artifacts)
        except Blocked as exc:
            return AgentResult(self.name, "blocked", f"Refused to patch: {exc}")
        print(f"\nHandoffs for {request.task_id}:\n{_handoffs(run.artifacts)}\n")
        print(f"Edit only {', '.join(approval.allowed_paths)} under {run.workspace}")
        intent = self.ask("When you are done, describe the change in one sentence: ").strip()
        return finish_patch(
            request.task_id,
            run,
            approval,
            self.mode,
            {"intent": intent or "(not described)", "rationale": "Repaired by hand.", "risks": []},
        )
