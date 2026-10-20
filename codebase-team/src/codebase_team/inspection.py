"""`codebase-team inspect`: reconstruct a run from its artifacts and trajectory alone."""

from __future__ import annotations

from pathlib import Path

from codebase_team.artifacts import (
    ApprovalRecord,
    Artifact,
    ArtifactError,
    ContextBrief,
    DiagnosisReport,
    PatchSummary,
    VerificationReport,
    read_artifact,
)
from codebase_team.trajectory import Trajectory
from codebase_team.workspace import Run, fingerprint


def _timeline(run: Run) -> list[str]:
    lines = []
    for e in Trajectory(run.trajectory_path).events():
        if e["event"] == "specialist_request":
            text = f"{e['agent']} <- {e['request_type']}"
        elif e["event"] == "specialist_result":
            touched = "  (changed the workspace)" if e["workspace_changed"] else ""
            text = f"{e['agent']} -> {e['status']}: {e['summary'][:90]}{touched}"
        elif e["event"] == "artifact_written":
            text = f"   wrote {Path(e['path']).name}"
        elif e["event"] in ("approval_proposed", "approval_recorded"):
            who = (
                "proposed"
                if e["event"] == "approval_proposed"
                else f"{e['approved_by']}: approved={e['approved']}"
            )
            text = f"approval {who} for {', '.join(e['allowed_paths']) or '(nothing)'}"
        else:
            detail = {k: v for k, v in e.items() if k not in ("seq", "timestamp", "event")}
            text = e["event"] + (f" {detail}" if detail else "")
        lines.append(f"  {e['seq']:>2}  {e['timestamp'][11:19]}  {text}")
    return lines


def _handoffs(run: Run) -> list[str]:
    out = []

    def load[A: Artifact](kind: type[A]) -> A | None:
        try:
            return read_artifact(run.artifacts, kind)
        except ArtifactError:
            return None

    if d := load(DiagnosisReport):
        out += [
            f"  Diagnosis ({d.status}): {d.observed_error or 'all checks passed'}",
            f"    cause: {d.suspected_cause}",
            f"    files: {', '.join(d.relevant_files)}",
        ]
    if b := load(ContextBrief):
        out += [
            f"  Context brief: {len(b.facts)} facts, notes {', '.join(b.relevant_memory_notes) or 'none'}"
        ]
        out += [f"    constraint: {c}" for c in b.suggested_constraints]
    if a := load(ApprovalRecord):
        out += [
            f"  Approval: approved={a.approved} by {a.approved_by} for {', '.join(a.allowed_paths)}"
            f" (commands: {', '.join(a.allowed_commands) or 'none'})"
        ]
    if p := load(PatchSummary):
        out += [f"  Patch ({p.mode}): {', '.join(p.files_changed) or 'no change'} - {p.intent}"]
    if v := load(VerificationReport):
        out += [f"  Verification ({v.status}): {v.recommendation}"]
    return out


def report(run: Run) -> str:
    meta = run.meta()
    source_ok = fingerprint(Path(meta["source"])) == meta["source_fingerprint"]
    lines = [
        f"Run {run.task_id}" + (f"  scenario: {meta['scenario']}" if meta["scenario"] else ""),
        f"  source {meta['source']} @ {(meta['source_head'] or '?')[:7]}: "
        + ("untouched" if source_ok else "CHANGED since the run started"),
        f"  workspace {run.workspace}: changed {', '.join(run.changed_files()) or 'nothing'}",
        "",
        "Trajectory:",
        *_timeline(run),
        "",
        "Handoffs:",
        *_handoffs(run),
    ]
    diff = run.diff_stat()
    if diff:
        lines += ["", "Workspace diff:", *(f"  {line}" for line in diff.splitlines())]
    return "\n".join(lines)
