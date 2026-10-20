"""The assembled Librarian, driven by a scripted model: tool surface, write boundary, memory writes."""

import json

from agent_kit.harness import text_of
from agent_kit.recording import RunRecorder
from agent_kit.testing import ScriptedModel, call, calls
from langchain_core.messages import AIMessage, ToolMessage

from librarian_agent.agent import LibrarianAgent
from librarian_agent.embeddings import HashingEmbedder

OWN_TOOLS = [
    "file_history",
    "git_log",
    "git_show",
    "list_memory_notes",
    "read_memory_note",
    "remember_decision",
    "retrieve_context",
]


def librarian(config, *replies):
    model = ScriptedModel(replies=list(replies))
    return LibrarianAgent(config, RunRecorder(config.memory_dir), HashingEmbedder(), model=model), model


def results(agent):
    return {m.tool_call_id: m for m in agent.messages if isinstance(m, ToolMessage)}


def test_the_librarian_is_offered_read_tools_and_its_own_memory_tools_only(config, index):
    agent, model = librarian(config, AIMessage(content="I find and remember; I do not edit."))
    agent.ask("What do you do?")
    assert model.offered_tools == sorted(["glob", "grep", "ls", "read_file", *OWN_TOOLS])
    system = text_of(model.seen[0][0].content)
    assert "You are the Librarian" in system and "Source of truth" in system
    for skill in ("answer-codebase-question", "remember-decision", "prepare-change-context"):
        assert skill in system


def test_the_codebase_cannot_be_written_and_secrets_cannot_be_read(config, index):
    agent, _ = librarian(
        config,
        calls(
            call("write_file", "w", file_path="/codebase/NOTES.md", content="x"),
            call(
                "edit_file",
                "e",
                file_path="/codebase/context/ARCHITECTURE.md",
                old_string="409",
                new_string="400",
            ),
            call("write_file", "m", file_path="/memory/notes/x.md", content="x"),
            call("read_file", "env", file_path="/codebase/.env"),
        ),
        AIMessage(content="done"),
    )
    agent.ask("try it")
    got = results(agent)
    assert all(got[i].status == "error" or "Error" in str(got[i].content) for i in ("w", "e", "m"))
    assert "hunter2" not in got["env"].content
    assert not (config.codebase_path / "NOTES.md").exists()
    assert "409" in (config.codebase_path / "context/ARCHITECTURE.md").read_text(encoding="utf-8")
    assert not (config.memory_dir / "notes").exists()


def test_remembering_through_the_tool_writes_a_note_and_makes_it_searchable(config, index):
    agent, _ = librarian(
        config,
        calls(
            call(
                "remember_decision",
                "r",
                title="Key format",
                statement="Keys allow letters, digits, . _ -",
                rationale="Keys appear in URLs.",
                sources=["user, 2026-10-20"],
                confidence=0.7,
            )
        ),
        calls(call("retrieve_context", "q", query="which characters may a key contain")),
        AIMessage(content="Remembered."),
    )
    agent.ask("Remember that keys allow letters, digits, dot, underscore and dash.")
    got = results(agent)
    saved = json.loads(got["r"].content)
    assert saved["indexed"] is True and (config.notes_dir / f"{saved['remembered']}.md").is_file()
    found = json.loads(got["q"].content)
    assert f"note:{saved['remembered']}" in [h["source"] for h in found["semantic_hits"]]


def test_refusals_come_back_as_tool_errors_not_crashes(config, index):
    agent, _ = librarian(
        config,
        calls(
            call("read_memory_note", "n", note_id="../../codebase/README"),
            call("git_show", "g", commit="--all"),
        ),
        AIMessage(content="ok"),
    )
    assert agent.ask("go") == "ok"
    got = results(agent)
    assert got["n"].status == "error" and "not a note id" in got["n"].content
    assert got["g"].status == "error" and "not a commit hash" in got["g"].content
