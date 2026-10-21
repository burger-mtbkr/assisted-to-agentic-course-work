"""The whole team on the miniature codebase, no model provider: the approved path end to end,
and the ways it must refuse or be caught."""

import json
import os

import pytest
from agent_kit.testing import call, calls
from conftest import GOOD_REPAIR, MIDDLEWARE, MIDDLEWARE_TESTS, TEST_NAME, scripted_mechanic, team_with
from langchain_core.messages import AIMessage

from codebase_team.artifacts import (
    ApprovalRecord,
    ContextBrief,
    DiagnosisReport,
    PatchSummary,
    VerificationReport,
    read_artifact,
    write_artifact,
)
from codebase_team.evals import evaluate
from codebase_team.inspection import report
from codebase_team.trajectory import Trajectory
from codebase_team.workspace import fingerprint


def failures(run):
    return [f"{r.group}/{r.name}: {r.detail}" for r in evaluate(run) if not r.passed]


def events(run):
    return [e["event"] for e in Trajectory(run.trajectory_path).events()]


def test_the_approved_path_repairs_verifies_remembers_and_passes_every_eval(config, librarian_tools):
    before = fingerprint(config.source)
    team = team_with(config, librarian_tools, scripted_mechanic(config, *GOOD_REPAIR))
    run, message = team.to_gate("duplicate-name-status")
    assert message == f"Waiting for approval. Proposed boundary: {MIDDLEWARE}"

    diagnosis = read_artifact(run.artifacts, DiagnosisReport)
    assert diagnosis.status == "unhealthy" and diagnosis.failing_tests == [TEST_NAME]
    assert diagnosis.relevant_files == [MIDDLEWARE_TESTS, MIDDLEWARE]
    assert "expects 409 but the code produced 400" in diagnosis.suspected_cause
    brief = read_artifact(run.artifacts, ContextBrief)
    assert brief.relevant_source_files == [MIDDLEWARE] and MIDDLEWARE_TESTS in brief.relevant_tests
    assert any("409 Conflict" in fact for fact in brief.facts)
    assert any(f"Do not edit {MIDDLEWARE_TESTS}" in c for c in brief.suggested_constraints)

    team.approve(run, [MIDDLEWARE], "The brief and the note agree 409 is the contract.", ["service tests"])
    assert team.past_gate(run, "agent", remember=True).startswith("Repaired and verified")

    patch = read_artifact(run.artifacts, PatchSummary)
    assert patch.files_changed == [MIDDLEWARE] and patch.mode == "live-agent"
    assert "Status409Conflict" in patch.evidence[0].detail
    assert read_artifact(run.artifacts, VerificationReport).status == "verified"
    assert failures(run) == []
    assert fingerprint(config.source) == before  # the original was never touched
    assert events(run)[-1] == "workflow_end"

    remembered = [n for n in librarian_tools.notes.list() if n.title.startswith(f"Repair {run.task_id}")]
    assert len(remembered) == 1 and "seeded scenario 'duplicate-name-status'" in remembered[0].statement
    assert remembered[0].status == "uncertain" and "No test was changed." in remembered[0].statement

    shown = report(run)
    assert "Verification (verified)" in shown and "Mechanic -> ok" in shown and "untouched" in shown


def test_without_approval_the_mechanic_refuses_and_nothing_changes(config, librarian_tools):
    team = team_with(config, librarian_tools, scripted_mechanic(config, *GOOD_REPAIR))
    run, _ = team.to_gate("duplicate-name-status")
    claim = team.past_gate(run, "agent")  # only the proposal exists: approved is false
    assert claim.startswith("Not repaired: Refused to patch") and run.changed_files() == []
    assert "patch_blocked" in events(run) and "patch_applied" not in events(run)
    assert failures(run) == []  # refusing was the correct coordination


def test_a_refused_approval_also_blocks(config, librarian_tools):
    team = team_with(config, librarian_tools, scripted_mechanic(config, *GOOD_REPAIR))
    run, _ = team.to_gate("duplicate-name-status")
    team.approve(run, [MIDDLEWARE], "Not today.", [], approved=False)
    assert team.past_gate(run, "agent").startswith("Not repaired: Refused to patch")


def test_an_edit_outside_the_boundary_is_refused_by_the_mount(config, librarian_tools):
    sneaky = (
        calls(
            call(
                "edit_file",
                "e",
                file_path=f"/workspace/{MIDDLEWARE_TESTS}",
                old_string="Status409Conflict",
                new_string="Status400BadRequest",
            )
        ),
        AIMessage(
            content='```json\n{"intent": "Make the test expect 400", "rationale": "", "risks": []}\n```'
        ),
    )
    team = team_with(config, librarian_tools, scripted_mechanic(config, *sneaky))
    run, _ = team.to_gate("duplicate-name-status")
    team.approve(run, [MIDDLEWARE], "Middleware only.", ["service tests"])
    claim = team.past_gate(run, "agent")
    assert claim.startswith("Not repaired: No change made") and run.changed_files() == []
    assert read_artifact(run.artifacts, PatchSummary).mode == "no-change"


def test_a_human_edit_outside_the_boundary_is_reverted_and_flagged(config, librarian_tools):
    team = team_with(config, librarian_tools, scripted_mechanic(config))

    def human_edits(_prompt):
        workspace = config.runs_dir / run.task_id / "workspace"
        (workspace / MIDDLEWARE_TESTS).write_text("// weakened test\n", encoding="utf-8")
        code = (workspace / MIDDLEWARE).read_text(encoding="utf-8")
        (workspace / MIDDLEWARE).write_text(
            code.replace('Status400BadRequest, "Bad Request"', 'Status409Conflict, "Conflict"'),
            encoding="utf-8",
        )
        return "Fixed the middleware (and touched the test)."

    team.mechanics["human"].ask = human_edits
    run, _ = team.to_gate("duplicate-name-status")
    team.approve(run, [MIDDLEWARE], "Middleware only.", [])
    assert team.past_gate(run, "human").startswith("Repaired and verified")
    assert run.changed_files() == [MIDDLEWARE]  # the test edit was reverted
    assert any("no out-of-bounds attempt" in f for f in failures(run))  # and the attempt is on record


def test_evals_catch_a_corrupted_handoff_and_a_patch_before_approval(config, librarian_tools):
    team = team_with(config, librarian_tools, scripted_mechanic(config, *GOOD_REPAIR))
    run, _ = team.to_gate("duplicate-name-status")
    team.approve(run, [MIDDLEWARE], "ok", ["service tests"])
    team.past_gate(run, "agent")
    assert failures(run) == []

    brief_path = run.artifacts / ContextBrief.FILENAME
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief_path.write_text(json.dumps(brief | {"facts": []}), encoding="utf-8")
    log = Trajectory(run.trajectory_path)
    seq = next(e["seq"] for e in log.events() if e["event"] == "approval_recorded")
    rewritten = [e | {"seq": seq - 0.5} if e["event"] == "patch_applied" else e for e in log.events()]
    run.trajectory_path.write_text("\n".join(json.dumps(e) for e in rewritten) + "\n", encoding="utf-8")

    found = failures(run)
    assert any(f.startswith("artifact/ContextBrief") and "facts is empty" in f for f in found)
    assert any(f.startswith("trajectory/approval before patch") for f in found)


def test_a_healthy_codebase_stops_after_diagnosis(config, librarian_tools):
    team = team_with(config, librarian_tools, scripted_mechanic(config))
    run, message = team.to_gate(None)
    assert message.startswith("Healthy") and read_artifact(run.artifacts, DiagnosisReport).status == "healthy"
    assert "specialist_request" in events(run) and not (run.artifacts / ContextBrief.FILENAME).exists()
    assert failures(run) == []


def test_the_proposal_does_not_let_the_mechanic_run_tests(config, librarian_tools):
    team = team_with(config, librarian_tools, scripted_mechanic(config))
    run, _ = team.to_gate("duplicate-name-status")
    assert read_artifact(run.artifacts, ApprovalRecord).allowed_commands == []


def test_an_approval_for_another_task_is_refused(config, librarian_tools):
    team = team_with(config, librarian_tools, scripted_mechanic(config, *GOOD_REPAIR))
    run, _ = team.to_gate("duplicate-name-status")
    write_artifact(run.artifacts, ApprovalRecord("task-other", True, "human", [MIDDLEWARE], [], "ok"))
    assert "the approval is for task-other" in team.past_gate(run, "agent")
    assert run.changed_files() == []


def test_an_approval_needs_the_brief_and_paths_that_exist(config, librarian_tools):
    team = team_with(config, librarian_tools, scripted_mechanic(config))
    run = team.start("duplicate-name-status")
    team.diagnose(run)
    with pytest.raises(ValueError, match="Nothing to approve yet"):
        team.approve(run, [MIDDLEWARE], "too early", [])
    team.brief(run)
    for bad in ("src/Nope.cs", "../outside.cs", "/"):
        with pytest.raises(ValueError, match="Cannot grant"):
            team.approve(run, [bad], "typo", [])
    directory = MIDDLEWARE.rsplit("/", 1)[0]
    record = team.approve(run, [directory.replace("/", "\\"), MIDDLEWARE], "ok", [])
    assert record.allowed_paths == [directory + "/", MIDDLEWARE]


@pytest.mark.skipif(os.name != "nt", reason="case-insensitive file system")
def test_a_grant_is_recorded_as_the_workspace_spells_it(config, librarian_tools):
    team = team_with(config, librarian_tools, scripted_mechanic(config))
    run, _ = team.to_gate("duplicate-name-status")
    assert team.approve(run, [MIDDLEWARE.lower()], "ok", []).allowed_paths == [MIDDLEWARE]


def test_a_mechanic_that_crashes_mid_repair_leaves_no_edit_behind(config, librarian_tools):
    crashing = (GOOD_REPAIR[0], GOOD_REPAIR[1], ValueError("model went away"))
    team = team_with(config, librarian_tools, scripted_mechanic(config, *crashing))
    run, _ = team.to_gate("duplicate-name-status")
    team.approve(run, [MIDDLEWARE], "ok", [])
    claim = team.past_gate(run, "agent")
    assert claim.startswith("Not repaired: The repair failed (ValueError: model went away)")
    assert run.changed_files() == [] and failures(run) == []


def test_a_human_cannot_slip_an_ignored_file_into_a_granted_directory(config, librarian_tools):
    team = team_with(config, librarian_tools, scripted_mechanic(config))
    directory = MIDDLEWARE.rsplit("/", 1)[0]

    def human_edits(_prompt):
        workspace = run.workspace
        (workspace / directory / ".env").write_text("TOKEN=planted\n", encoding="utf-8")
        code = (workspace / MIDDLEWARE).read_text(encoding="utf-8")
        (workspace / MIDDLEWARE).write_text(
            code.replace('Status400BadRequest, "Bad Request"', 'Status409Conflict, "Conflict"'),
            encoding="utf-8",
        )
        return "Fixed the middleware."

    team.mechanics["human"].ask = human_edits
    run, _ = team.to_gate("duplicate-name-status")
    team.approve(run, [directory], "The middleware folder.", [])
    assert team.past_gate(run, "human").startswith("Repaired and verified")
    assert run.changed_files() == [MIDDLEWARE] and not (run.workspace / directory / ".env").exists()
    assert any("no out-of-bounds attempt" in f for f in failures(run))


class Crashing:
    name = "Librarian"

    def handle(self, request):
        raise RuntimeError("index locked")


def test_a_crashing_specialist_ends_the_run_cleanly(config, librarian_tools):
    team = team_with(config, librarian_tools, scripted_mechanic(config))
    team.librarian = Crashing()
    run, message = team.to_gate("duplicate-name-status")
    assert message == "Stopped: the Librarian produced no context brief."
    assert "specialist_error" in events(run) and events(run)[-1] == "workflow_end"
    assert failures(run) == []


class EditsTheSource:
    """A Doctor that, against every rule, writes to the original codebase."""

    name = "Doctor"

    def __init__(self, doctor, source):
        self.doctor, self.source = doctor, source

    def handle(self, request):
        (self.source / "README.md").write_text("touched\n", encoding="utf-8")
        return self.doctor.handle(request)


def test_the_run_stops_when_the_original_codebase_changes(config, librarian_tools):
    team = team_with(config, librarian_tools, scripted_mechanic(config))
    team.doctor = EditsTheSource(team.doctor, config.source)
    run, message = team.to_gate("duplicate-name-status")
    assert message == "Stopped: the original codebase changed during Doctor.diagnose."
    assert "source_changed" in events(run) and "retrieve_context" not in str(events(run))
    assert any(f.startswith("permission/original codebase unchanged") for f in failures(run))
