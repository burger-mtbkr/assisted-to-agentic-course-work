"""The Doctor on the team: the Module 7 Doctor's sensors, run in the run workspace.

It diagnoses before any edit and verifies after one. It reads only the files the failure
output names (the failing test at its line, and the code that test is named after), and
it never writes to the workspace.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from agent_kit.mount import visible_files
from doctor_agent.tools import run_check

from codebase_team.artifacts import (
    AgentRequest,
    AgentResult,
    DiagnosisReport,
    Evidence,
    PatchSummary,
    VerificationReport,
    read_artifact,
    write_artifact,
)

FAILED_TEST = re.compile(r"^\s*Failed (\S+) \[", re.M)
SUMMARY = re.compile(
    r"(?:Passed|Failed)!\s+-\s+Failed:\s+(\d+), Passed:\s+(\d+), Skipped:\s+(\d+), Total:\s+(\d+)"
)
FRAME = re.compile(r" in (.+?):line (\d+)")
BUILD_PROBLEM = re.compile(r"^.*: (?:error|warning) [A-Z]+\d*:.*$", re.M)
FULL_OUTPUT = 200_000


@dataclass
class TestFailure:
    name: str
    message: str
    frames: list[tuple[str, int]] = field(default_factory=list)

    @property
    def method(self) -> str:
        return self.name.rsplit(".", 1)[-1]

    @property
    def subject(self) -> str:
        """The identifier a test is about, by this codebase's naming: `Subject_Behaviour`."""
        return self.method.split("_", 1)[0]


def relative(path: str, workspace: Path) -> str | None:
    """A path from compiler or test output, relative to the workspace (None if outside)."""
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(workspace.resolve()).as_posix()
    except ValueError:
        return None


def parse_failures(output: str, workspace: Path) -> list[TestFailure]:
    failures = []
    starts = [m.start() for m in FAILED_TEST.finditer(output)]
    for begin, end in zip(starts, [*starts[1:], len(output)], strict=True):
        block = output[begin:end]
        name = FAILED_TEST.match(block).group(1)
        message = block.split("Error Message:", 1)[-1].split("Stack Trace:", 1)[0]
        frames = [
            (rel, int(line)) for path, line in FRAME.findall(block) if (rel := relative(path, workspace))
        ]
        failures.append(TestFailure(name, " ".join(message.split()), frames))
    return failures


def implementation_of(test_file: str, workspace: Path) -> str | None:
    """`FooTests.cs` tests `Foo.cs`, outside the test project."""
    name = PurePosixPath(test_file).name
    if not name.endswith("Tests.cs"):
        return None
    wanted = name.removesuffix("Tests.cs") + ".cs"
    matches = [
        p for p in visible_files(workspace) if PurePosixPath(p).name == wanted and ".UnitTests/" not in p
    ]
    return matches[0] if len(matches) == 1 else None


def excerpt(workspace: Path, path: str, around: int, radius: int = 4) -> str:
    lines = (workspace / path).read_text(encoding="utf-8", errors="replace").splitlines()
    first, last = max(around - radius, 1), min(around + radius, len(lines))
    return "\n".join(f"{n}: {lines[n - 1]}" for n in range(first, last + 1))


def lines_mentioning(workspace: Path, path: str, identifier: str) -> str:
    lines = (workspace / path).read_text(encoding="utf-8", errors="replace").splitlines()
    hits = [i for i, line in enumerate(lines, start=1) if identifier in line]
    return "\n".join(excerpt(workspace, path, hit, radius=2) for hit in hits[:2])


class DoctorAdapter:
    name = "Doctor"

    def __init__(self, test_command: str, lint_command: str, timeout_seconds: int):
        self.test_command = test_command
        self.lint_command = lint_command
        self.timeout_seconds = timeout_seconds

    def handle(self, request: AgentRequest) -> AgentResult:
        workspace, artifacts = Path(request.inputs["workspace"]), Path(request.inputs["artifacts"])
        if request.request_type == "diagnose":
            return self.diagnose(request.task_id, workspace, artifacts)
        if request.request_type == "verify":
            return self.verify(request.task_id, workspace, artifacts)
        return AgentResult(self.name, "failed", f"The Doctor does not handle {request.request_type!r}.")

    def _checks(self, workspace: Path) -> tuple[dict[str, Any], dict[str, Any]]:
        tests = run_check(
            "run_tests", "service tests", self.test_command, workspace, self.timeout_seconds, FULL_OUTPUT
        )
        lint = run_check(
            "run_lint", "service lint", self.lint_command, workspace, self.timeout_seconds, FULL_OUTPUT
        )
        return tests, lint

    @staticmethod
    def _check_evidence(result: dict[str, Any]) -> Evidence:
        summary = SUMMARY.search(result["stdout"])
        detail = (
            f"exit {result['exit_code']}: failed {summary[1]}, passed {summary[2]}, skipped {summary[3]} "
            f"of {summary[4]}"
            if summary
            else result.get("error") or f"exit {result['exit_code']}"
        )
        return Evidence(f"`{result['command']}` ({result['duration_ms']} ms)", "command", detail)

    def diagnose(self, task_id: str, workspace: Path, artifacts: Path) -> AgentResult:
        tests, lint = self._checks(workspace)
        evidence = [self._check_evidence(tests), self._check_evidence(lint)]
        failures = parse_failures(tests["stdout"], workspace)
        lint_problems = BUILD_PROBLEM.findall(lint["stdout"] + lint["stderr"])[:10]
        relevant: list[str] = []
        for failure in failures:
            evidence.append(Evidence(failure.name, "command", failure.message))
            for path, line in failure.frames[:1]:
                relevant.append(path)
                evidence.append(Evidence(f"{path}:{line}", "test", excerpt(workspace, path, line)))
                if (code := implementation_of(path, workspace)) and (
                    quoted := lines_mentioning(workspace, code, failure.subject)
                ):
                    relevant.append(code)
                    evidence.append(
                        Evidence(code, "source", f"where {failure.subject} is handled:\n{quoted}")
                    )
        evidence += [Evidence("lint output", "command", problem.strip()) for problem in lint_problems]

        incomplete = [r for r in (tests, lint) if r.get("error")]
        failing = [r["check"] for r in (tests, lint) if not r["passed"]]
        status = "inconclusive" if incomplete else ("unhealthy" if failing else "healthy")
        if failures:
            first = failures[0]
            expected = re.search(r"Expected: (\S+)", first.message)
            actual = re.search(r"Actual: (\S+)", first.message)
            observed = f"{first.method}: {first.message}"
            code_files = [p for p in relevant if ".UnitTests/" not in p]
            cause = (
                f"{first.method} expects {expected[1]} but the code produced {actual[1]}"
                if expected and actual
                else f"{first.method} fails"
            ) + (f"; the code under test is {code_files[0]}" if code_files else "")
            uncertainty = [
                "The checks show the test and the code disagree; they cannot say which one is the contract. "
                "Docs, the API contract and remembered decisions should settle that before any edit."
            ]
            next_step = (
                "Ask the Librarian which side is the contract, and for the narrowest safe edit boundary."
            )
        elif failing:
            observed = (
                (incomplete[0].get("error") if incomplete else None)
                or "; ".join(lint_problems)
                or (f"{', '.join(failing)} failed without a parsable failure line")
            )
            cause = "See the check output; no single failing test identifies the code."
            uncertainty = ["No test failure names a file, so the evidence points nowhere specific."]
            next_step = "Read the full check output before choosing a repair boundary."
        else:
            observed, cause, uncertainty = "", "", []
            next_step = "Nothing to repair: every check passed."
        report = DiagnosisReport(
            task_id=task_id,
            status=status,
            failing_checks=failing,
            failing_tests=[f.name for f in failures],
            observed_error=observed,
            relevant_files=list(dict.fromkeys(relevant)),
            suspected_cause=cause,
            evidence=evidence,
            uncertainty=uncertainty,
            recommended_next_step=next_step,
        )
        path = write_artifact(artifacts, report)
        return AgentResult(
            self.name,
            "ok" if status != "inconclusive" else "inconclusive",
            f"{status}: {observed or 'all checks passed'}",
            artifacts=[str(path)],
            evidence=evidence[:2],
            confidence=0.9 if failures or status == "healthy" else 0.5,
            next_actions=[next_step],
        )

    def verify(self, task_id: str, workspace: Path, artifacts: Path) -> AgentResult:
        patch = read_artifact(artifacts, PatchSummary)
        diagnosis = read_artifact(artifacts, DiagnosisReport)
        tests, lint = self._checks(workspace)
        evidence = [self._check_evidence(tests), self._check_evidence(lint)]
        failures = parse_failures(tests["stdout"], workspace)
        evidence += [Evidence(f.name, "command", f.message) for f in failures]
        incomplete = any(r.get("error") for r in (tests, lint))
        passed = tests["passed"] and lint["passed"]
        status = "inconclusive" if incomplete else ("verified" if passed else "failed")
        fixed = [t for t in diagnosis.failing_tests if t not in {f.name for f in failures}]
        if fixed:
            evidence.append(Evidence("service tests", "command", f"now passing: {', '.join(fixed)}"))
        recommendation = {
            "verified": "Accept the patch: every check passes, including the one the diagnosis saw fail.",
            "failed": "Do not accept: checks still fail. Debug backward from the remaining failures.",
            "inconclusive": "Re-run the checks: they did not complete, so nothing is verified.",
        }[status]
        report = VerificationReport(
            task_id=task_id,
            status=status,
            checks_run=[tests["check"], lint["check"]],
            passed=bool(passed and not incomplete),
            remaining_failures=[f.name for f in failures] + ([] if lint["passed"] else [lint["check"]]),
            files_inspected=patch.files_changed,
            evidence=evidence,
            recommendation=recommendation,
        )
        path = write_artifact(artifacts, report)
        return AgentResult(self.name, "ok", f"{status}: {recommendation}", [str(path)], evidence[:2], 0.9)
