"""Episodic memory from Git: scoped, read-only, and refusing anything that is not a path or a hash."""

import pytest
from conftest import git

from librarian_agent.history import GitHistory, HistoryError


def test_log_lists_commits_newest_first(codebase):
    commits = GitHistory(codebase).log()["commits"]
    assert [c["subject"] for c in commits] == ["Add ErrorMiddleware and flags", "Document the error contract"]
    assert commits[0]["author"] == "Tester" and len(commits[0]["date"]) == 10


def test_log_and_file_history_scope_to_a_path(codebase):
    history = GitHistory(codebase)
    assert [c["subject"] for c in history.log("context")["commits"]] == ["Document the error contract"]
    assert [
        c["subject"] for c in history.file_history("src/Api/Middleware/ErrorMiddleware.cs")["commits"]
    ] == ["Add ErrorMiddleware and flags"]


def test_file_history_follows_renames(codebase):
    git(codebase, "mv", "src/Api/Models/Flag.cs", "src/Api/Models/FeatureFlag.cs")
    git(codebase, "commit", "-q", "-m", "Rename Flag")
    subjects = [
        c["subject"] for c in GitHistory(codebase).file_history("src/Api/Models/FeatureFlag.cs")["commits"]
    ]
    assert subjects == ["Rename Flag", "Add ErrorMiddleware and flags"]


def test_show_returns_message_files_and_diff(codebase):
    history = GitHistory(codebase)
    commit = history.log()["commits"][0]["commit"]
    shown = history.show(commit)
    assert shown["message"] == "Add ErrorMiddleware and flags"
    assert (
        "ErrorMiddleware.cs" in shown["files_in_codebase"]
        and "+public class ErrorMiddleware" in shown["diff"]
    )
    assert ".env" not in shown["diff"]  # never tracked, so never in history


@pytest.mark.parametrize("path", ["../outside", "/codebase/../x", "C:/Windows", "--output=x", "a/../../b"])
def test_paths_outside_the_codebase_are_refused(codebase, path):
    with pytest.raises(HistoryError, match="not a path inside the codebase"):
        GitHistory(codebase).log(path)


@pytest.mark.parametrize("commit", ["HEAD; rm -rf /", "--all", "main", "zzzz"])
def test_only_commit_hashes_are_shown(codebase, commit):
    with pytest.raises(HistoryError, match="not a commit hash"):
        GitHistory(codebase).show(commit)


def test_mount_style_and_rooted_paths_mean_codebase_paths(codebase):
    history = GitHistory(codebase)
    assert history.log("/codebase/context")["scope"] == "context"
    assert history.file_history("/src/Api/Models/Flag.cs")["path"] == "src/Api/Models/Flag.cs"
    assert history.log("/etc/passwd")["commits"] == []  # a codebase-relative path with no history
