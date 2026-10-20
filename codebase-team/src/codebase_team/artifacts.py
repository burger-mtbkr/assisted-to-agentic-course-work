"""The team's contracts: the common request/result every specialist speaks, and the five
handoff artifacts that move work from one specialist to the next.

Each artifact validates itself. A malformed or incomplete artifact is a failed handoff,
reported by name, never silently passed on.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, ClassVar, Self

EVIDENCE_KINDS = ("test", "source", "doc", "memory", "git", "command", "diff", "human")


class ArtifactError(ValueError):
    """An artifact is missing, malformed, or incomplete for its receiver."""


@dataclass
class Evidence:
    source: str
    kind: str
    detail: str


@dataclass
class AgentRequest:
    task_id: str
    request_type: str  # diagnose | retrieve_context | patch | verify | remember_repair
    instructions: str
    inputs: dict[str, str] = field(default_factory=dict)  # artifact name -> path
    constraints: dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""


@dataclass
class AgentResult:
    agent: str
    status: str  # ok | blocked | failed | needs_approval | inconclusive
    summary: str
    artifacts: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    confidence: float | None = None
    next_actions: list[str] = field(default_factory=list)


@dataclass
class Artifact:
    FILENAME: ClassVar[str] = ""

    def problems(self) -> list[str]:
        """What is missing for the receiver to act on; empty when the artifact is usable."""
        found = []
        for item in getattr(self, "evidence", []):
            if item.kind not in EVIDENCE_KINDS:
                found.append(f"evidence kind {item.kind!r} is not one of {', '.join(EVIDENCE_KINDS)}")
            if not (item.source and item.detail):
                found.append("every evidence item needs a source and a detail")
        return found

    def validate(self) -> Self:
        if found := self.problems():
            raise ArtifactError(f"{type(self).__name__} is incomplete: " + "; ".join(found))
        return self

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        names = {f.name for f in fields(cls)}
        if missing := sorted(names - set(data)):
            raise ArtifactError(f"{cls.__name__} is missing {', '.join(missing)}")
        values = {k: v for k, v in data.items() if k in names}
        if "evidence" in values:
            values["evidence"] = [Evidence(**e) if isinstance(e, dict) else e for e in values["evidence"]]
        return cls(**values)


def _missing(artifact: Artifact, *names: str) -> list[str]:
    return [f"{name} is empty" for name in names if not getattr(artifact, name)]


@dataclass
class DiagnosisReport(Artifact):
    FILENAME: ClassVar[str] = "diagnosis.json"
    task_id: str
    status: str  # healthy | unhealthy | inconclusive
    failing_checks: list[str]
    failing_tests: list[str]
    observed_error: str
    relevant_files: list[str]
    suspected_cause: str
    evidence: list[Evidence]
    uncertainty: list[str]
    recommended_next_step: str

    def problems(self) -> list[str]:
        found = super().problems() + _missing(self, "task_id", "evidence", "recommended_next_step")
        if self.status not in ("healthy", "unhealthy", "inconclusive"):
            found.append(f"status {self.status!r} is not healthy, unhealthy or inconclusive")
        if self.status != "healthy":
            found += _missing(self, "failing_checks", "observed_error")
        return found


@dataclass
class ContextBrief(Artifact):
    FILENAME: ClassVar[str] = "context_brief.json"
    task_id: str
    relevant_docs: list[str]
    relevant_memory_notes: list[str]
    relevant_source_files: list[str]
    relevant_tests: list[str]
    git_evidence: list[str]
    facts: list[str]
    suggested_constraints: list[str]
    gaps: list[str]
    evidence: list[Evidence]
    confidence: float

    def problems(self) -> list[str]:
        found = super().problems() + _missing(self, "task_id", "facts", "evidence")
        if not (self.suggested_constraints or self.gaps):
            found.append("a brief needs suggested constraints or stated gaps")
        return found


@dataclass
class ApprovalRecord(Artifact):
    FILENAME: ClassVar[str] = "approval.json"
    task_id: str
    approved: bool
    approved_by: str
    allowed_paths: list[str]
    allowed_commands: list[str]
    rationale: str

    def problems(self) -> list[str]:
        found = super().problems() + _missing(self, "task_id", "approved_by", "rationale")
        if not isinstance(self.approved, bool):
            found.append("approved must be true or false")
        if self.approved:
            found += _missing(self, "allowed_paths")
        return found


@dataclass
class PatchSummary(Artifact):
    FILENAME: ClassVar[str] = "patch_summary.json"
    task_id: str
    mode: str  # live-agent | human-assisted | no-change
    intent: str
    files_changed: list[str]
    diff_summary: str
    rationale: str
    risks: list[str]
    verification_request: str
    evidence: list[Evidence]

    def problems(self) -> list[str]:
        found = super().problems() + _missing(self, "task_id", "mode", "intent")
        if self.mode != "no-change":
            found += _missing(self, "files_changed", "diff_summary", "verification_request", "evidence")
        return found


@dataclass
class VerificationReport(Artifact):
    FILENAME: ClassVar[str] = "verification.json"
    task_id: str
    status: str  # verified | failed | inconclusive
    checks_run: list[str]
    passed: bool
    remaining_failures: list[str]
    files_inspected: list[str]
    evidence: list[Evidence]
    recommendation: str

    def problems(self) -> list[str]:
        found = super().problems() + _missing(self, "task_id", "checks_run", "evidence", "recommendation")
        if self.status not in ("verified", "failed", "inconclusive"):
            found.append(f"status {self.status!r} is not verified, failed or inconclusive")
        if (self.status == "verified") != (self.passed is True and not self.remaining_failures):
            found.append("status 'verified' requires passed checks and no remaining failures, and vice versa")
        return found


HANDOFFS: tuple[type[Artifact], ...] = (
    DiagnosisReport,
    ContextBrief,
    ApprovalRecord,
    PatchSummary,
    VerificationReport,
)


def write_artifact(directory: Path, artifact: Artifact) -> Path:
    artifact.validate()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / artifact.FILENAME
    path.write_text(artifact.to_json() + "\n", encoding="utf-8")
    return path


def read_artifact[A: Artifact](directory: Path, kind: type[A]) -> A:
    path = directory / kind.FILENAME
    if not path.is_file():
        raise ArtifactError(f"{kind.__name__} not found: {path.name} has not been written")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ArtifactError(f"{path.name} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ArtifactError(f"{path.name} is not a JSON object")
    try:
        return kind.from_dict(data).validate()
    except TypeError as exc:
        raise ArtifactError(f"{path.name} is malformed: {exc}") from exc
