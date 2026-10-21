"""The check tools: structured evidence, failures as data, head-and-tail compaction."""

import json
import os
import threading
import time

from conftest import py

from doctor_agent.tools import DiagnosticTools, run_check

FIELDS = {"tool", "check", "command", "cwd", "exit_code", "passed", "duration_ms", "stdout", "stderr"}


def test_a_passing_check_returns_structured_evidence(codebase):
    result = run_check("run_tests", "tests", py("print(42)"), codebase, 30)
    assert FIELDS <= result.keys()
    assert result["passed"] is True and result["exit_code"] == 0 and result["stdout"] == "42"
    assert result["cwd"] == str(codebase) and result["duration_ms"] >= 0


def test_a_failing_check_is_evidence_not_an_exception(codebase):
    command = py("import sys; print('boom', file=sys.stderr); sys.exit(3)")
    result = run_check("run_lint", "lint", command, codebase, 30)
    assert result["passed"] is False and result["exit_code"] == 3 and result["stderr"] == "boom"


def test_checks_run_in_the_codebase_directory(codebase):
    result = run_check("run_tests", "tests", py("import os; print(os.getcwd())"), codebase, 30)
    assert os.path.samefile(result["stdout"], codebase)


def test_a_missing_codebase_is_reported(tmp_path):
    result = run_check("run_tests", "tests", py("print(1)"), tmp_path / "gone", 30)
    assert result["passed"] is False and result["exit_code"] is None
    assert "Codebase not found" in result["error"]


def test_a_command_that_cannot_run_fails_the_check(codebase):
    result = run_check("run_tests", "tests", "no-such-command-xyz", codebase, 30)
    assert result["passed"] is False and result["exit_code"] != 0


def test_a_timeout_stops_the_whole_process_tree(codebase):
    # The check spawns a grandchild that would hold the output pipe open for a minute.
    sleeper = "[sys.executable, '-c', 'import time; time.sleep(60)']"
    spawn = f"import subprocess, sys, time; subprocess.Popen({sleeper}); time.sleep(60)"
    result = run_check("run_tests", "tests", py(spawn), codebase, 2)
    assert result["passed"] is False and result["exit_code"] is None
    assert "Timed out after 2s" in result["error"] and "were stopped" in result["error"]
    assert result["duration_ms"] < 15_000


def test_a_timeout_also_stops_orphans_whose_parent_already_exited(codebase, tmp_path):
    # check -> middle -> sleeper; middle exits at once, so the sleeper's parent is gone
    # and taskkill /T could not find it - but it still holds the check's output pipe.
    middle = tmp_path / "middle.py"
    middle.write_text(
        "import subprocess, sys\nsubprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n",
        encoding="utf-8",
    )
    spawn = f"import subprocess, sys, time; subprocess.run([sys.executable, r'{middle}']); time.sleep(60)"
    result = run_check("run_tests", "tests", py(spawn), codebase, 2)
    assert "were stopped" in result["error"] and result["duration_ms"] < 15_000


def test_both_checks_never_run_at_the_same_time(codebase):
    nap = py("import time; time.sleep(1.5)")
    tools = DiagnosticTools(codebase, nap, nap, 30)
    started = time.perf_counter()
    workers = [threading.Thread(target=tools.run_tests), threading.Thread(target=tools.run_lint)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    assert time.perf_counter() - started >= 3.0  # one after the other, never overlapping


def test_checks_get_only_what_toolchains_need(codebase, monkeypatch):
    for name, value in {
        "GEMINI_API_KEY": "k",
        "AWS_SECRET_ACCESS_KEY": "s",
        "GITHUB_TOKEN": "t",
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
    }.items():
        monkeypatch.setenv(name, value)
    names = (
        "['GEMINI_API_KEY', 'AWS_SECRET_ACCESS_KEY', 'GITHUB_TOKEN', 'DOTNET_CLI_TELEMETRY_OPTOUT', 'PATH']"
    )
    command = py(f"import os; print([n in os.environ for n in {names}])")
    assert (
        run_check("run_tests", "tests", command, codebase, 30)["stdout"]
        == "[False, False, False, True, True]"
    )


def test_tools_take_no_arguments_and_return_json(config):
    tools = DiagnosticTools(config.codebase_path, config.test_command, config.lint_command, 30)
    by_name = {t.name: t for t in tools.as_langchain_tools()}
    assert set(by_name) == {"run_tests", "run_lint"}
    assert all(not t.args for t in by_name.values())
    tests = json.loads(by_name["run_tests"].invoke({}))
    lint = json.loads(by_name["run_lint"].invoke({}))
    assert tests["tool"] == "run_tests" and tests["passed"] is True
    assert lint["tool"] == "run_lint" and lint["passed"] is False and "CS0168" in lint["stdout"]
