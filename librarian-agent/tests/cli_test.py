"""The command surface end to end with the hashing embedder: seed, index, retrieve, inspect -
plus the startup refusals."""

import json

import pytest
from conftest import PROJECT_ROOT

from librarian_agent.cli import main
from librarian_agent.config import ConfigError, LibrarianConfig
from librarian_agent.notes import NoteStore
from librarian_agent.seeds import SEEDS, seed


@pytest.fixture
def env(codebase, tmp_path, monkeypatch):
    monkeypatch.setenv("LIBRARIAN_CODEBASE_PATH", str(codebase))
    monkeypatch.setenv("LIBRARIAN_KNOWLEDGE_DIR", str(codebase / "knowledge"))
    monkeypatch.setenv("LIBRARIAN_MEMORY_DIR", str(tmp_path / "memory"))
    monkeypatch.setenv("LIBRARIAN_EMBEDDINGS", "hashing")
    return tmp_path / "memory"


def test_seed_index_retrieve_and_inspect(env, capsys):
    assert main(["seed"]) == 0
    assert main(["seed"]) == 0  # idempotent
    assert len(list((env / "notes").glob("*.md"))) == len(SEEDS)
    assert main(["index"]) == 0
    assert "Indexed 8 files" in capsys.readouterr().out

    assert main(["retrieve", "Why do duplicate names return 409?"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["memories"] and result["memories"][0]["title"].startswith("Duplicate names")

    assert main(["inspect"]) == 0
    report = capsys.readouterr().out
    assert f"Notes (notes/): {len(SEEDS)}" in report and "built by hashing-512" in report
    assert "notes: in step with the index" in report and "Why do duplicate names return 409?" in report

    assert main(["inspect", "--retrieval", "latest"]) == 0
    assert "recommended:" in capsys.readouterr().out


def test_inspect_shows_drift_between_notes_files_and_codebase_and_the_index(env, codebase, capsys):
    main(["index"])
    NoteStore(env / "notes").remember(title="Later", statement="s", rationale="r", sources=["user"])
    (codebase / "context" / "NEW.md").write_text("# New\n", encoding="utf-8")
    (env / "notes" / "2026-10-20-broken.md").write_text("not a note\n", encoding="utf-8")
    capsys.readouterr()
    main(["inspect"])
    report = capsys.readouterr().out
    assert "notes not indexed: " in report and "added:   context/NEW.md" in report
    assert "UNREADABLE: 2026-10-20-broken.md" in report and "run `librarian index`" in report


def test_chat_without_a_key_is_a_clear_refusal(env, monkeypatch, capsys):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    assert main(["chat", "--ask", "hi"]) == 2
    assert "GEMINI_API_KEY is not set" in capsys.readouterr().err


def test_memory_inside_the_codebase_is_refused(env, codebase, monkeypatch):
    monkeypatch.setenv("LIBRARIAN_MEMORY_DIR", str(codebase / "src" / ".memory"))
    with pytest.raises(ConfigError, match="inside the codebase"):
        LibrarianConfig.load()


def test_unknown_embedder_setting_is_refused(env, monkeypatch):
    monkeypatch.setenv("LIBRARIAN_EMBEDDINGS", "magic")
    with pytest.raises(ConfigError, match="LIBRARIAN_EMBEDDINGS"):
        LibrarianConfig.load()


def test_seeds_cite_files_that_exist_in_config_service(notes):
    config_service = PROJECT_ROOT.parent / "config-service"
    missing = [src for s in SEEDS for src in s["sources"] if not (config_service / src).is_file()]
    assert missing == []
    written = seed(notes)
    assert [n.title for n in written] == [s["title"] for s in SEEDS]
    assert all(n.confidence >= 0.9 for n in written)
