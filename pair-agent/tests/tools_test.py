"""The tool registry and the harness's read-only repo tools."""

import subprocess

import pytest

from pair_agent.tools import MAX_RESULT_CHARS, RepoTools, Tool, ToolError, ToolOutcome, ToolRegistry


def tool(name, handler):
    return Tool(name, "d", {"type": "object"}, handler, "harness")


async def test_sync_and_async_handlers_and_structured_results():
    async def async_handler():
        return {"a": 1}

    registry = ToolRegistry()
    registry.register(tool("sync", lambda: "plain"))
    registry.register(tool("async", async_handler))
    assert await registry.execute("sync", {}) == ToolOutcome("plain", False)
    assert await registry.execute("async", {}) == ToolOutcome('{\n  "a": 1\n}', False)


async def test_failures_become_error_outcomes():
    def boom():
        raise RuntimeError("kaput")

    def refuse():
        raise ToolError("nicely explained")

    registry = ToolRegistry()
    registry.register(tool("boom", boom))
    registry.register(tool("refuse", refuse))
    assert await registry.execute("boom", {}) == ToolOutcome("boom failed: RuntimeError: kaput", True)
    assert await registry.execute("refuse", {}) == ToolOutcome("nicely explained", True)
    bad_args = await registry.execute("refuse", {"unexpected": 1})
    assert bad_args.is_error and bad_args.content.startswith("Invalid arguments for refuse")


async def test_large_results_are_capped():
    registry = ToolRegistry()
    registry.register(tool("big", lambda: "x" * (MAX_RESULT_CHARS + 10)))
    outcome = await registry.execute("big", {})
    assert outcome.content.endswith(f"kept {MAX_RESULT_CHARS}]")


def test_duplicate_names_are_rejected():
    registry = ToolRegistry()
    registry.register(tool("t", lambda: None))
    with pytest.raises(ValueError):
        registry.register(tool("t", lambda: None))


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "Flag.cs").write_text("line one\nFlagKey here\nline three\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(".env\n", encoding="utf-8")
    (tmp_path / ".env").write_text("API_SECRET=hunter2\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    return RepoTools(tmp_path)


def test_read_file_numbers_lines_and_honours_the_range(repo):
    assert repo.read_file("src/Flag.cs", 2, 3) == "src/Flag.cs lines 2-3 of 3\n    2  FlagKey here\n    3  line three"


def test_read_file_refuses_paths_outside_the_repo(repo):
    with pytest.raises(ToolError, match="outside the repository"):
        repo.read_file("../secrets.txt")


def test_read_file_missing_file_is_a_clear_error(repo):
    with pytest.raises(ToolError, match="No such file"):
        repo.read_file("src/Nope.cs")


def test_search_code_finds_and_reports_misses(repo):
    assert repo.search_code("flagkey") == "src/Flag.cs:2:FlagKey here"
    assert repo.search_code("absent") == "No matches for 'absent'."


def test_read_file_refuses_git_ignored_secrets(repo):
    with pytest.raises(ToolError, match="git-ignored"):
        repo.read_file(".env")


def test_untracked_but_not_ignored_files_are_readable(repo):
    (repo.root / "src" / "New.cs").write_text("work in progress\n", encoding="utf-8")
    assert "work in progress" in repo.read_file("src/New.cs")


def test_search_code_clamps_max_results(repo):
    assert repo.search_code("line", max_results=0) == "src/Flag.cs:1:line one\n[1 more matches not shown]"
    assert repo.search_code("line", max_results=-5).startswith("src/Flag.cs:1:line one")
