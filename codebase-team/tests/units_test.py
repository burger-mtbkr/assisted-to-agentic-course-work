"""The parts on their own: handoff validation, the run workspace, the scenario, the Doctor's
parser (on output captured from the real `dotnet test` run), and the Mechanic's report parser."""

import json
import sys
from pathlib import Path

import pytest
from conftest import MIDDLEWARE

from codebase_team.artifacts import (
    ApprovalRecord,
    ArtifactError,
    ContextBrief,
    DiagnosisReport,
    Evidence,
    PatchSummary,
    VerificationReport,
    read_artifact,
    write_artifact,
)
from codebase_team.doctor import DoctorAdapter, parse_failures
from codebase_team.doctor import test_counts as count_tests  # aliased: pytest would collect test_*
from codebase_team.mechanic import parse_report
from codebase_team.scenarios import ScenarioError, apply
from codebase_team.workspace import create_run, fingerprint

CMD = Evidence("`npm run test:api`", "command", "exit 1")
COUNTS = {"failed": 1, "passed": 2, "skipped": 0, "total": 3}


def diagnosis(**changes):
    fields = dict(
        task_id="t",
        status="unhealthy",
        failing_checks=["service tests"],
        failing_tests=["T"],
        observed_error="Expected 409, got 400",
        relevant_files=[MIDDLEWARE],
        suspected_cause="c",
        evidence=[CMD],
        uncertainty=[],
        recommended_next_step="Ask the Librarian",
        test_counts=COUNTS,
    )
    return DiagnosisReport(**(fields | changes))


@pytest.mark.parametrize(
    ("artifact", "problem"),
    [
        (diagnosis(failing_checks=[]), "failing_checks is empty"),
        (diagnosis(evidence=[]), "evidence is empty"),
        (diagnosis(status="sick"), "status 'sick'"),
        (diagnosis(evidence=[Evidence("x", "rumour", "d")]), "evidence kind 'rumour'"),
        (ContextBrief("t", [], [], [], [], [], [], [], [], [CMD], 0.5), "facts is empty"),
        (
            ContextBrief("t", [], [], [], [], [], ["f"], [], [], [CMD], 0.5),
            "suggested constraints or stated gaps",
        ),
        (ApprovalRecord("t", True, "human", [], [], "why"), "allowed_paths is empty"),
        (ApprovalRecord("t", "yes", "human", ["a"], [], "why"), "approved must be true or false"),
        (PatchSummary("t", "live-agent", "i", [], "", "", [], "", []), "files_changed is empty"),
        (
            VerificationReport("t", "verified", ["tests"], False, [], [], [CMD], "r", COUNTS),
            "status 'verified' requires",
        ),
    ],
)
def test_incomplete_handoffs_are_refused_by_name(artifact, problem):
    with pytest.raises(ArtifactError, match=problem):
        artifact.validate()


def test_a_healthy_diagnosis_needs_no_failure_and_a_blocked_patch_no_diff():
    diagnosis(status="healthy", failing_checks=[], observed_error="").validate()
    PatchSummary("t", "no-change", "nothing to do", [], "", "", [], "", []).validate()


def test_artifacts_round_trip_and_bad_files_are_reported(tmp_path):
    written = diagnosis()
    write_artifact(tmp_path, written)
    assert read_artifact(tmp_path, DiagnosisReport) == written
    with pytest.raises(ArtifactError, match="has not been written"):
        read_artifact(tmp_path, ContextBrief)
    (tmp_path / "approval.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ArtifactError, match="not valid JSON"):
        read_artifact(tmp_path, ApprovalRecord)
    (tmp_path / "verification.json").write_text(json.dumps({"task_id": "t"}), encoding="utf-8")
    with pytest.raises(ArtifactError, match="missing checks_run"):
        read_artifact(tmp_path, VerificationReport)


def test_a_run_copies_only_visible_files_seeds_the_scenario_and_leaves_the_source_alone(source, tmp_path):
    before = fingerprint(source)
    first = create_run(source, tmp_path / "runs", "duplicate-name-status")
    second = create_run(source, tmp_path / "runs")
    assert first.root != second.root
    assert not (first.workspace / ".env").exists() and (first.workspace / ".gitignore").exists()
    assert "Status400BadRequest" in (first.workspace / MIDDLEWARE).read_text(encoding="utf-8")
    assert "Status409Conflict" in (second.workspace / MIDDLEWARE).read_text(encoding="utf-8")
    assert first.changed_files() == []  # the scenario is part of the baseline
    assert fingerprint(source) == before and first.meta()["source_fingerprint"] == before

    (first.workspace / MIDDLEWARE).write_text("changed\n", encoding="utf-8")
    (first.workspace / "NEW.cs").write_text("new\n", encoding="utf-8")
    assert first.changed_files() == ["NEW.cs", MIDDLEWARE] and "+new" in first.diff()
    first.revert(["NEW.cs", MIDDLEWARE])
    assert first.changed_files() == []


def test_unknown_or_stale_scenarios_are_refused(source, tmp_path):
    with pytest.raises(ScenarioError, match="Unknown scenario"):
        apply(source, "nope")
    (source / MIDDLEWARE).write_text("already different\n", encoding="utf-8")
    with pytest.raises(ScenarioError, match="no longer contains"):
        apply(source, "duplicate-name-status")


REAL_DOTNET_OUTPUT = r"""
A total of 1 test files matched the specified pattern.
  Failed ConfigApi.Service.UnitTests.Middleware.ErrorMiddlewareTests.DuplicateApplicationNameException_MapsTo409 [1 ms]
  Error Message:
   Assert.Equal() Failure: Values differ
Expected: 409
Actual:   400
  Stack Trace:
     at ConfigApi.Service.UnitTests.Middleware.ErrorMiddlewareTests.DuplicateApplicationNameException_MapsTo409() in {ws}\src\ConfigApi.Service.UnitTests\Middleware\ErrorMiddlewareTests.cs:line 41
--- End of stack trace from previous location ---

Failed!  - Failed:     1, Passed:    86, Skipped:     0, Total:    87, Duration: 880 ms - ConfigApi.Service.UnitTests.dll (net10.0)
"""  # noqa: E501 - verbatim dotnet output


def test_the_parser_reads_real_dotnet_failure_output(tmp_path):
    [failure] = parse_failures(REAL_DOTNET_OUTPUT.replace("{ws}", str(tmp_path)), tmp_path)
    assert failure.method == "DuplicateApplicationNameException_MapsTo409"
    assert failure.subject == "DuplicateApplicationNameException"
    assert failure.message == "Assert.Equal() Failure: Values differ Expected: 409 Actual: 400"
    assert failure.frames == [("src/ConfigApi.Service.UnitTests/Middleware/ErrorMiddlewareTests.cs", 41)]
    assert parse_failures("Passed!  - Failed:     0, Passed:    87", tmp_path) == []
    outside = REAL_DOTNET_OUTPUT.replace("{ws}", str(Path(tmp_path).parent / "elsewhere"))
    assert parse_failures(outside, tmp_path)[0].frames == []  # frames outside the workspace are ignored


def test_a_theory_case_is_one_failure_named_by_its_method():
    output = (
        '  Failed Ns.KeysTests.Key_IsValid(key: "a b") [2 ms]\n  Error Message:\n   boom\n'
        "Failed!  - Failed:     1, Passed:    40, Skipped:     2, Total:    43, Duration: 9 ms - A.dll\n"
        "Passed!  - Failed:     0, Passed:     5, Skipped:     0, Total:     5, Duration: 1 ms - B.dll\n"
    )
    [failure] = parse_failures(output, Path.cwd())
    assert failure.name == 'Ns.KeysTests.Key_IsValid(key: "a b")' and failure.method == "Key_IsValid"
    assert count_tests(output) == {"failed": 1, "passed": 45, "skipped": 2, "total": 48}


def test_a_verification_with_fewer_tests_than_the_diagnosis_is_not_verified(tmp_path):
    artifacts = tmp_path / "artifacts"
    write_artifact(artifacts, diagnosis(task_id="t"))
    write_artifact(
        artifacts,
        PatchSummary(
            "t", "live-agent", "i", [MIDDLEWARE], "1 file", "r", [], "v", [Evidence("d", "diff", "x")]
        ),
    )
    passing = "Passed!  - Failed:     0, Passed:     2, Skipped:     0, Total:     2, Duration: 1 ms"
    command = f'"{sys.executable}" -c "print(\'{passing}\')"'
    doctor = DoctorAdapter(command, f'"{sys.executable}" -c "print(1)"', 60)
    doctor.verify("t", tmp_path, artifacts)
    report = read_artifact(artifacts, VerificationReport)
    assert report.status == "failed" and "test count fell from 3 to 2" in report.remaining_failures
    assert report.test_counts["total"] == 2 and not any("now passing" in e.detail for e in report.evidence)


def test_evidence_items_must_have_exactly_their_three_fields(tmp_path):
    data = json.loads(diagnosis().to_json())
    (tmp_path / DiagnosisReport.FILENAME).write_text(
        json.dumps(data | {"evidence": [{"source": "s", "kind": "command"}]}), encoding="utf-8"
    )
    with pytest.raises(ArtifactError, match="exactly source, kind and detail"):
        read_artifact(tmp_path, DiagnosisReport)
    (tmp_path / DiagnosisReport.FILENAME).write_text(
        json.dumps(data | {"failing_tests": "T"}), encoding="utf-8"
    )
    with pytest.raises(ArtifactError, match="failing_tests must be a list"):
        read_artifact(tmp_path, DiagnosisReport)


def test_a_deleted_file_is_a_change_the_diff_shows(source, tmp_path):
    run = create_run(source, tmp_path / "runs")
    (run.workspace / MIDDLEWARE).unlink()
    index_before = (run.workspace / ".git" / "index").read_bytes()
    assert run.changed_files() == [MIDDLEWARE] and "deleted file mode" in run.diff()
    assert (run.workspace / ".git" / "index").read_bytes() == index_before  # reading changed nothing
    run.revert([MIDDLEWARE])
    assert run.changed_files() == [] and (run.workspace / MIDDLEWARE).is_file()


def test_the_mechanic_report_is_read_from_its_json_block_or_falls_back_to_text():
    text = 'Done.\n```json\n{"intent": "Restore 409", "rationale": "contract", "risks": "none known"}\n```'
    assert parse_report(text) == {"intent": "Restore 409", "rationale": "contract", "risks": ["none known"]}
    assert parse_report("Changed the status code.\nIt was 400.")["intent"] == "Changed the status code."
