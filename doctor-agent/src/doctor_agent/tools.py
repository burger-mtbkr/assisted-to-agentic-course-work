"""The Doctor's sensors: the codebase's own test and lint commands, run as tools.

The model decides *whether* to run a check, never *what* runs - the commands are
configuration, and the tools take no arguments.
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from agent_kit.recording import OUTPUT_LIMIT, compact
from langchain_core.tools import StructuredTool

from doctor_agent.processes import ProcessTree

DRAIN_SECONDS = 10  # after a kill, how long to wait for the last output


def run_check(
    tool: str, check: str, command: str, cwd: Path, timeout_seconds: int, output_limit: int = OUTPUT_LIMIT
) -> dict[str, Any]:
    """Run one check command in `cwd` and return structured evidence; never raises.

    Output is compacted to `output_limit` characters for the model; a program parsing the
    output (the Module 9 Doctor adapter) can ask for more."""
    started = time.perf_counter()
    result: dict[str, Any] = {"tool": tool, "check": check, "command": command, "cwd": str(cwd)}

    def finish(**fields: Any) -> dict[str, Any]:
        return {**result, **fields, "duration_ms": round((time.perf_counter() - started) * 1000)}

    if not cwd.is_dir():
        return finish(exit_code=None, passed=False, stdout="", stderr="", error=f"Codebase not found: {cwd}")
    try:
        tree = ProcessTree(command, cwd)
    except OSError as exc:
        return finish(exit_code=None, passed=False, stdout="", stderr="", error=f"Could not start: {exc}")
    try:
        stdout, stderr = tree.process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        tree.kill()
        error = f"Timed out after {timeout_seconds}s; the check and everything it started were stopped."
        try:
            stdout, stderr = tree.process.communicate(timeout=DRAIN_SECONDS)
        except subprocess.TimeoutExpired:  # something outside the tree still holds the pipes
            stdout, stderr = "", ""
            error = f"Timed out after {timeout_seconds}s; some processes it started could not be stopped."
        return finish(
            exit_code=None,
            passed=False,
            stdout=compact(stdout, output_limit),
            stderr=compact(stderr, output_limit),
            error=error,
        )
    finally:
        tree.close()
    return finish(
        exit_code=tree.process.returncode,
        passed=tree.process.returncode == 0,
        stdout=compact(stdout, output_limit),
        stderr=compact(stderr, output_limit),
    )


class DiagnosticTools:
    def __init__(self, codebase: Path, test_command: str, lint_command: str, timeout_seconds: int):
        self.codebase = codebase
        self.test_command = test_command
        self.lint_command = lint_command
        self.timeout_seconds = timeout_seconds
        # The model may ask for both checks in one step, and Deep Agents runs parallel calls
        # in threads; `dotnet test` and `dotnet build` share bin/ and obj/, so take turns.
        self._one_at_a_time = threading.Lock()

    def run_tests(self) -> dict[str, Any]:
        with self._one_at_a_time:
            return run_check("run_tests", "tests", self.test_command, self.codebase, self.timeout_seconds)

    def run_lint(self) -> dict[str, Any]:
        with self._one_at_a_time:
            return run_check("run_lint", "lint", self.lint_command, self.codebase, self.timeout_seconds)

    def as_langchain_tools(self) -> list[StructuredTool]:
        """The checks as model-callable tools, each returning its evidence as JSON."""
        return [
            StructuredTool.from_function(
                func=lambda: json.dumps(self.run_tests(), ensure_ascii=False),
                name="run_tests",
                description=(
                    "Run the codebase's own test suite and return structured evidence: command, exit_code, "
                    "passed, duration_ms, stdout, stderr. The primary health sensor - run it before making "
                    f"any health claim. Can take a minute or more. Command: {self.test_command}"
                ),
            ),
            StructuredTool.from_function(
                func=lambda: json.dumps(self.run_lint(), ensure_ascii=False),
                name="run_lint",
                description=(
                    "Run the codebase's lint/static-analysis gate and return the same structured evidence. "
                    f"Can take a minute or more. Command: {self.lint_command}"
                ),
            ),
        ]
