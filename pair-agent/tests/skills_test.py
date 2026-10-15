"""Skill discovery, progressive disclosure, and script execution."""

import os
from pathlib import Path

import pytest

from pair_agent import skills as skills_module
from pair_agent.skills import SkillCatalog, read_frontmatter
from pair_agent.tools import ToolError

REPO_SKILLS = Path(__file__).resolve().parents[2] / ".claude" / "skills"


def write_skill(root: Path, name: str, frontmatter: str, body: str = "BODY", script: str | None = None):
    directory = root / name
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n{body}\n", encoding="utf-8")
    if script is not None:
        (directory / "script.sh").write_text(script, encoding="utf-8", newline="\n")
    return directory


def test_catalog_holds_metadata_only_and_skips_dirs_without_skill_md(tmp_path):
    write_skill(tmp_path, "alpha", "name: alpha\ndescription: Does alpha things.", body="SECRET BODY")
    (tmp_path / "_lib").mkdir()
    catalog = SkillCatalog(tmp_path, tmp_path)
    assert catalog.list_skills() == [
        {"name": "alpha", "description": "Does alpha things.", "location": str((tmp_path / "alpha").resolve())},
    ]
    assert "SECRET BODY" not in repr(catalog.list_skills())


def test_activation_loads_the_full_body_and_bundled_files(tmp_path):
    write_skill(tmp_path, "alpha", "name: alpha\ndescription: d", body="FULL BODY", script="echo hi\n")
    result = SkillCatalog(tmp_path, tmp_path).activate_skill("alpha")
    assert "FULL BODY" in result["instructions"]
    assert result["bundled_files"] == ["script.sh"]
    assert Path(result["base_directory"]).name == "alpha"


def test_unknown_skill_names_the_known_ones(tmp_path):
    write_skill(tmp_path, "alpha", "name: alpha\ndescription: d")
    with pytest.raises(ToolError, match="Known skills: alpha"):
        SkillCatalog(tmp_path, tmp_path).activate_skill("beta")


def test_unquoted_colon_in_description_falls_back_to_literal_fields(tmp_path):
    directory = write_skill(tmp_path, "alpha", "name: alpha\ndescription: Produces a brief: the active task.")
    assert read_frontmatter(directory / "SKILL.md") == {
        "name": "alpha",
        "description": "Produces a brief: the active task.",
    }


def test_repo_skills_are_discovered():
    names = SkillCatalog(REPO_SKILLS, REPO_SKILLS).names()
    assert {"launch-work-item", "land-work-item"} <= set(names)
    assert "_lib" not in names


def test_find_bash_prefers_path_bash_over_the_wsl_launcher(tmp_path, monkeypatch):
    system32 = tmp_path / "Windows" / "System32"
    git_bin = tmp_path / "Git" / "bin"
    for directory in (system32, git_bin):
        directory.mkdir(parents=True)
        (directory / "bash.exe").write_bytes(b"")
        (directory / "bash").write_bytes(b"")
        os.chmod(directory / "bash", 0o755)
    monkeypatch.delenv("PAIR_AGENT_BASH", raising=False)
    monkeypatch.setenv("SystemRoot", str(tmp_path / "Windows"))
    monkeypatch.setenv("PATH", os.pathsep.join([str(system32), str(git_bin)]))
    assert Path(skills_module.find_bash()).parent == git_bin


def catalog_with_script(tmp_path, script: str, timeout: float = 600) -> SkillCatalog:
    work = tmp_path / "work"
    work.mkdir()
    write_skill(tmp_path / "skills", "alpha", "name: alpha\ndescription: d", script=script)
    return SkillCatalog(tmp_path / "skills", work, script_timeout=timeout)


def test_script_runs_in_the_work_dir_and_reports_failure(tmp_path):
    catalog = catalog_with_script(tmp_path, 'echo "cwd=$(basename "$PWD") args=$*"\nexit 3\n')
    catalog.activate_skill("alpha")
    outcome = catalog.run_skill_script("alpha", ["--x", "y"])
    assert outcome.is_error
    assert "exit code 3" in outcome.content
    assert "cwd=work args=--x y" in outcome.content


def test_script_needs_the_skill_activated_first(tmp_path):
    catalog = catalog_with_script(tmp_path, "echo ran\n")
    with pytest.raises(ToolError, match="Activate the skill first"):
        catalog.run_skill_script("alpha")


@pytest.mark.parametrize("args, message", [
    ("--with-check", "list of strings"),
    (["--project-dir", "."], "--project-dir is not allowed"),
    (["--project-dir=."], "--project-dir is not allowed"),
    (["--work-item", "../outside.md"], "outside the code directory"),
    (["--work-item", "C:/Users/someone/secrets.txt"], "outside the code directory"),
])
def test_script_arguments_cannot_escape_the_code_directory(tmp_path, args, message):
    catalog = catalog_with_script(tmp_path, "echo ran\n")
    catalog.activate_skill("alpha")
    with pytest.raises(ToolError, match=message):
        catalog.run_skill_script("alpha", args)


def test_arguments_inside_the_code_directory_are_passed_through(tmp_path):
    catalog = catalog_with_script(tmp_path, 'echo "args=$*"\n')
    catalog.activate_skill("alpha")
    outcome = catalog.run_skill_script("alpha", ["--work-item", "002", "changes/002-x.md"])
    assert not outcome.is_error and "args=--work-item 002 changes/002-x.md" in outcome.content


def test_hung_script_times_out(tmp_path):
    catalog = catalog_with_script(tmp_path, "sleep 5\n", timeout=0.5)
    catalog.activate_skill("alpha")
    with pytest.raises(ToolError, match="did not finish"):
        catalog.run_skill_script("alpha")
