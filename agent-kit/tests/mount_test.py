"""GitScopedBackend: only git-visible files are seen, links are not followed, nothing is written."""

import os
import subprocess

import pytest

from agent_kit.mount import GitScopedBackend, normalize, visible_files


def git(cwd, *args):
    subprocess.run(
        ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "codebase"
    (root / "src" / "Api").mkdir(parents=True)
    (root / "node_modules" / "lib").mkdir(parents=True)
    (root / "src" / "Api" / "App.cs").write_text(
        "class App { // SECRET_NAME used here\n}\n", encoding="utf-8"
    )
    (root / "README.md").write_text("# Codebase\nSee SECRET_NAME docs.\n", encoding="utf-8")
    (root / ".gitignore").write_text(".env\nnode_modules/\n", encoding="utf-8")
    (root / ".env").write_text("SECRET_NAME=hunter2\n", encoding="utf-8")
    (root / "node_modules" / "lib" / "index.js").write_text("// SECRET_NAME\n", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "baseline")
    (root / "NOTES.md").write_text("untracked but not ignored\n", encoding="utf-8")
    return root


def test_visible_files_are_tracked_plus_untracked_not_ignored(repo):
    assert visible_files(repo) == [".gitignore", "NOTES.md", "README.md", "src/Api/App.cs"]


def test_a_deleted_tracked_file_is_not_visible(repo):
    (repo / "README.md").unlink()
    assert "README.md" not in visible_files(repo)


def test_falls_back_to_a_pruned_walk_outside_git(tmp_path):
    (tmp_path / "svc").mkdir()
    (tmp_path / "svc" / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=1\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("SECRET=\n", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "lib.py").write_text("", encoding="utf-8")
    assert visible_files(tmp_path) == [".env.example", "svc/app.py"]


def test_falls_back_when_the_enclosing_repo_ignores_the_root(tmp_path):
    (tmp_path / ".gitignore").write_text("fixture/\n", encoding="utf-8")
    git(tmp_path, "init", "-q")
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "app.py").write_text("", encoding="utf-8")
    (fixture / ".env").write_text("SECRET=1\n", encoding="utf-8")
    assert visible_files(fixture) == ["app.py"]


def test_ls_hides_ignored_entries(repo):
    entries = {e["path"] for e in GitScopedBackend(repo).ls("/").entries}
    assert entries == {"/.gitignore", "/NOTES.md", "/README.md", "/src/"}


def test_read_refuses_ignored_files_and_reads_visible_ones(repo):
    backend = GitScopedBackend(repo)
    refused = backend.read("/.env")
    assert refused.error and "git ignores it" in refused.error and refused.file_data is None
    assert GitScopedBackend(repo).read("/node_modules/lib/index.js").file_data is None
    assert "class App" in backend.read("/src/Api/App.cs").file_data["content"]


def test_read_cannot_escape_the_root(repo, tmp_path):
    (tmp_path / "outside.txt").write_text("outside\n", encoding="utf-8")
    result = GitScopedBackend(repo).read("/../outside.txt")
    assert result.file_data is None and result.error


def test_download_refuses_ignored_files(repo):
    responses = GitScopedBackend(repo).download_files(["/.env", "/README.md"])
    assert responses[0].error == "permission_denied" and responses[0].content is None
    assert responses[1].error is None and b"Codebase" in responses[1].content


def test_grep_searches_only_visible_files(repo):
    result = GitScopedBackend(repo).grep("SECRET_NAME")
    assert [(m["path"], m["line"]) for m in result.matches] == [("/README.md", 2), ("/src/Api/App.cs", 1)]
    assert not result.truncated


def test_grep_honours_path_glob_and_max_count(repo):
    backend = GitScopedBackend(repo)
    assert [m["path"] for m in backend.grep("SECRET_NAME", "/src").matches] == ["/src/Api/App.cs"]
    assert [m["path"] for m in backend.grep("SECRET_NAME", glob="*.md").matches] == ["/README.md"]
    assert [m["path"] for m in backend.grep("SECRET_NAME", "/README.md").matches] == ["/README.md"]
    assert backend.grep("SECRET_NAME", "/.env").matches == []
    capped = backend.grep("SECRET_NAME", max_count=1)
    assert len(capped.matches) == 1 and capped.truncated


def test_grep_rejects_context_lines(repo):
    with pytest.raises(ValueError):
        GitScopedBackend(repo).grep("x", context_lines=2)


def test_glob_matches_visible_files_only(repo):
    backend = GitScopedBackend(repo)
    assert [m["path"] for m in backend.glob("*.cs").matches] == ["/src/Api/App.cs"]
    assert [m["path"] for m in backend.glob("*.js").matches] == []
    assert [m["path"] for m in backend.glob("**/*.cs", "/src").matches] == ["/src/Api/App.cs"]


def test_every_write_is_refused(repo):
    backend = GitScopedBackend(repo)
    assert "read-only" in backend.write("/new.txt", "x").error
    assert "read-only" in backend.edit("/README.md", "Codebase", "Hacked").error
    assert "read-only" in backend.delete("/README.md").error
    assert backend.upload_files([("/up.txt", b"x")])[0].error == "permission_denied"
    assert (repo / "README.md").read_text(encoding="utf-8").startswith("# Codebase")
    assert not (repo / "new.txt").exists() and not (repo / "up.txt").exists()


def test_paths_outside_the_root_are_errors_not_exceptions(repo):
    backend = GitScopedBackend(repo)
    assert backend.ls("/../").error and backend.ls("/../").entries is None
    assert backend.grep("x", "/../").matches == []
    assert backend.glob("*", "/../").matches == []


def link(alias, target):
    """A directory link the way an unprivileged user can make one: a junction on Windows."""
    if os.name == "nt":
        command = ["cmd", "/c", "mklink", "/J", str(alias), str(target)]
        subprocess.run(command, check=True, capture_output=True)
    else:
        alias.symlink_to(target, target_is_directory=True)


def test_links_cannot_smuggle_in_ignored_or_outside_files(repo, tmp_path):
    (repo / ".gitignore").write_text(".env\nnode_modules/\nsecrets/\n", encoding="utf-8")
    (repo / "secrets").mkdir()
    (repo / "secrets" / "aws.txt").write_text("hunter2\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "host.txt").write_text("hunter2\n", encoding="utf-8")
    link(repo / "alias", repo / "secrets")
    link(repo / "away", outside)

    backend = GitScopedBackend(repo)
    assert not any(name.startswith(("alias/", "away/")) for name in backend.visible())
    for path in ("/alias/aws.txt", "/away/host.txt"):
        result = backend.read(path)
        assert result.file_data is None and result.error
    assert backend.grep("hunter2").matches == []
    assert backend.glob("*.txt").matches == []


def test_an_ignored_root_still_obeys_its_own_gitignore(tmp_path):
    (tmp_path / ".gitignore").write_text("fixture/\n", encoding="utf-8")
    git(tmp_path, "init", "-q")
    fixture = tmp_path / "fixture"
    (fixture / "svc" / "htmlcov").mkdir(parents=True)
    (fixture / ".gitignore").write_text("htmlcov/\n*.egg-info/\n", encoding="utf-8")
    (fixture / "svc" / "app.py").write_text("", encoding="utf-8")
    (fixture / "svc" / "htmlcov" / "index.html").write_text("", encoding="utf-8")
    (fixture / "svc" / ".env").write_text("SECRET=1\n", encoding="utf-8")
    assert visible_files(fixture) == [".gitignore", "svc/app.py"]


def test_grep_line_numbers_agree_with_read_file_offsets(repo):
    # read_file counts form feeds and lone carriage returns as line breaks; grep must too,
    # so that "line N" from grep is offset N-1 for read_file.
    (repo / "NOTES.md").write_bytes(b"one\x0cstill one\rtwo\r\nthree\nTARGET\n")
    backend = GitScopedBackend(repo)
    [match] = backend.grep("TARGET").matches
    window = backend.read("/NOTES.md", offset=match["line"] - 1, limit=1).file_data["content"]
    assert window.strip() == "TARGET" and match["line"] == 5


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("/src/Api/App.cs", "src/Api/App.cs"),
        ("./src/", "src"),
        ("src\\Api\\App.cs", "src/Api/App.cs"),
        ("/", ""),
    ],
)
def test_normalize(raw, expected):
    assert normalize(raw) == expected
