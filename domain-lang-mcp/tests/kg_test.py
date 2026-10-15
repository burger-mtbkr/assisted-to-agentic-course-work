"""Error mapping in the subprocess wrapper, with an injected runner."""

import asyncio
import json
from pathlib import Path

import pytest

from domain_lang_mcp import kg


def fake_runner(returncode: int, stdout: str = "", stderr: str = ""):
    calls: list[tuple[str, ...]] = []

    async def runner(settings, args):
        calls.append(args)
        return kg.CliResult(returncode, stdout, stderr)

    runner.calls = calls
    return runner


@pytest.fixture
def settings(tmp_path: Path) -> kg.KgSettings:
    db = tmp_path / "knowledge.db"
    db.write_bytes(b"")
    return kg.KgSettings(project_dir=tmp_path, db=db, timeout_seconds=5)


async def test_options_precede_the_term_so_option_like_terms_are_looked_up(settings):
    runner = fake_runner(0, json.dumps({"id": "x"}))
    await kg.query_json(settings, "lookup", "--help", runner=runner)
    assert runner.calls == [("lookup", "--format", "json", "--db", str(settings.db), "--", "--help")]


async def test_unset_kg_db_is_not_configured_rather_than_silently_empty(tmp_path):
    settings = kg.KgSettings(project_dir=tmp_path, db=None, timeout_seconds=5)
    runner = fake_runner(0, "[]")
    with pytest.raises(kg.KgServiceError) as err:
        await kg.query_json(settings, "list-areas", runner=runner)
    assert err.value.reason == "not_configured" and "KG_DB" in err.value.detail
    assert runner.calls == []


async def test_missing_uv_is_backend_unreachable(settings, monkeypatch):
    async def no_uv(*args, **kwargs):
        raise FileNotFoundError("uv")

    monkeypatch.setattr(kg.asyncio, "create_subprocess_exec", no_uv)
    with pytest.raises(kg.KgServiceError) as err:
        await kg.query_json(settings, "list-areas")
    assert err.value.reason == "backend_unreachable"


async def test_slow_cli_times_out_and_is_killed(settings, monkeypatch):
    class Hung:
        returncode = None
        killed = False

        async def communicate(self):
            await asyncio.sleep(10)

        def kill(self):
            self.killed = True
            self.returncode = -9

        async def wait(self):
            return self.returncode

    proc = Hung()

    async def spawn(*args, **kwargs):
        assert kwargs["stdin"] == asyncio.subprocess.DEVNULL
        return proc

    monkeypatch.setattr(kg.asyncio, "create_subprocess_exec", spawn)
    fast = kg.KgSettings(project_dir=settings.project_dir, db=settings.db, timeout_seconds=0.05)
    with pytest.raises(kg.KgServiceError) as err:
        await kg.query_json(fast, "list-areas")
    assert err.value.reason == "timeout"
    assert proc.killed


async def test_not_found_on_exit_1_is_a_normal_answer(settings):
    runner = fake_runner(1, json.dumps({"error": "not_found", "term": "nope"}))
    assert await kg.query_json(settings, "lookup", "nope", runner=runner) == {
        "error": "not_found",
        "term": "nope",
    }


async def test_exit_1_without_not_found_payload_is_cli_failed(settings):
    runner = fake_runner(1, "[]", "boom")
    with pytest.raises(kg.KgServiceError) as err:
        await kg.query_json(settings, "related", "x", runner=runner)
    assert err.value.reason == "cli_failed"


async def test_usage_error_exit_2_is_cli_failed_with_stderr_tail(settings):
    runner = fake_runner(2, "", "Usage: knowledge-graph\nError: No such option: --db")
    with pytest.raises(kg.KgServiceError) as err:
        await kg.query_json(settings, "lookup", "x", runner=runner)
    assert err.value.reason == "cli_failed"
    assert "No such option" in err.value.detail


async def test_non_json_stdout_is_malformed_output(settings):
    runner = fake_runner(0, "Traceback (most recent call last): ...")
    with pytest.raises(kg.KgServiceError) as err:
        await kg.query_json(settings, "lookup", "x", runner=runner)
    assert err.value.reason == "malformed_output"


async def test_unset_project_dir_is_not_configured():
    settings = kg.KgSettings(project_dir=None, db=None, timeout_seconds=5)
    with pytest.raises(kg.KgServiceError) as err:
        await kg.query_json(settings, "list-areas", runner=fake_runner(0, "[]"))
    assert err.value.reason == "not_configured"


async def test_missing_project_dir_is_backend_unreachable(tmp_path):
    settings = kg.KgSettings(project_dir=tmp_path / "gone", db=None, timeout_seconds=5)
    runner = fake_runner(0, "[]")
    with pytest.raises(kg.KgServiceError) as err:
        await kg.query_json(settings, "list-areas", runner=runner)
    assert err.value.reason == "backend_unreachable"
    assert runner.calls == []


async def test_missing_db_is_reported_before_the_cli_can_create_an_empty_one(tmp_path):
    settings = kg.KgSettings(project_dir=tmp_path, db=tmp_path / "gone.db", timeout_seconds=5)
    runner = fake_runner(1, json.dumps({"error": "not_found", "term": "x"}))
    with pytest.raises(kg.KgServiceError) as err:
        await kg.query_json(settings, "lookup", "x", runner=runner)
    assert err.value.reason == "knowledge_db_missing"
    assert "import" in err.value.fix
    assert runner.calls == []


async def test_validate_exit_0_is_valid(settings):
    assert await kg.validate(settings, runner=fake_runner(0, "knowledge graph is valid\n")) == {
        "valid": True,
        "issues": [],
    }


async def test_validate_exit_1_lists_issues(settings):
    runner = fake_runner(1, "edge references missing to_node 'a'\nedge references missing to_node 'b'\n")
    assert await kg.validate(settings, runner=runner) == {
        "valid": False,
        "issues": ["edge references missing to_node 'a'", "edge references missing to_node 'b'"],
    }


async def test_validate_crash_is_not_reported_as_issues(settings):
    with pytest.raises(kg.KgServiceError) as err:
        await kg.validate(settings, runner=fake_runner(2, "", "error: Failed to spawn"))
    assert err.value.reason == "cli_failed"


def test_service_error_payload_shape():
    payload = kg.KgServiceError("timeout", "slow", "retry").to_payload()
    assert payload == {"error": "service_error", "reason": "timeout", "detail": "slow", "fix": "retry"}
