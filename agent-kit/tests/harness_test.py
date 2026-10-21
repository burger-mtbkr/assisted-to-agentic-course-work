"""The shared harness: an assembled agent's tool surface, and how a Session records turns."""

import json
import subprocess

import pytest
from deepagents import FilesystemPermission
from deepagents.backends import FilesystemBackend
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langchain_google_genai.chat_models import GoogleAPIError, GoogleRateLimitError
from recording_test import read_jsonl

from agent_kit.harness import (
    FINAL_ROUND,
    STOPPED,
    RoundBudget,
    Session,
    assemble,
    result_fields,
    skill_read,
    text_of,
    transient,
)
from agent_kit.mount import GitScopedBackend
from agent_kit.recording import RunRecorder
from agent_kit.testing import ScriptedModel, call, calls

OVERLOADED = GoogleAPIError(code=503, response_json={"error": {"status": "UNAVAILABLE"}})
EXCLUDED = frozenset({"write_file", "edit_file", "delete", "execute", "write_todos", "task"})


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "codebase"
    root.mkdir()
    (root / "README.md").write_text("# Patient\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    skills = tmp_path / "skills" / "check-things"
    skills.mkdir(parents=True)
    (skills / "SKILL.md").write_text(
        "---\nname: check-things\ndescription: Use when checking things.\n---\n"
        "# Check things\n1. run_check\n",
        encoding="utf-8",
    )
    return root, tmp_path / "skills"


def session_for(model, workspace, tmp_path):
    root, skills = workspace
    run_check = StructuredTool.from_function(
        func=lambda: json.dumps({"passed": False, "exit_code": 1, "stdout": "3 passed, 1 failed"}),
        name="run_check",
        description="Run the check.",
    )
    graph = assemble(
        model,
        system_prompt="You are a test specialist.",
        tools=[run_check],
        routes={
            "/codebase/": GitScopedBackend(root),
            "/skills/": FilesystemBackend(skills, virtual_mode=True),
        },
        excluded_tools=EXCLUDED,
        permissions=[FilesystemPermission(operations=["write"], paths=["/**"], mode="deny")],
    )
    recorder = RunRecorder(tmp_path / "runs")
    return Session(graph, recorder), recorder


def test_the_model_is_offered_the_mount_tools_and_ours_only(workspace, tmp_path):
    model = ScriptedModel(replies=[AIMessage(content="hello")])
    session, _ = session_for(model, workspace, tmp_path)
    assert session.ask("hi") == "hello"
    assert model.offered_tools == ["glob", "grep", "ls", "read_file", "run_check"]
    system = text_of(model.seen[0][0].content)
    assert "You are a test specialist." in system and "check-things" in system  # skill catalog, not body
    assert "1. run_check" not in system


def test_a_turn_is_recorded_in_the_conversation_and_the_trace(workspace, tmp_path):
    model = ScriptedModel(
        replies=[
            calls(call("read_file", "s", file_path="/skills/check-things/SKILL.md")),
            calls(call("run_check", "c"), call("read_file", "r", file_path="/codebase/README.md")),
            AIMessage(content="Unhealthy: 1 failed."),
        ]
    )
    session, recorder = session_for(model, workspace, tmp_path)
    events = [e for e in session.stream("check it") if e["type"] != "token"]

    assert [e["type"] for e in events] == [
        "tool_call",
        "tool_result",
        "tool_call",
        "tool_call",
        "tool_result",
        "tool_result",
        "final",
    ]
    assert events[-1]["text"] == "Unhealthy: 1 failed."
    said = read_jsonl(recorder.conversation_path)
    assert [r["event"] for r in said] == [
        "user_message",
        "tool_call",
        "skill_read",
        "tool_result",
        "tool_call",
        "tool_call",
        "tool_result",
        "tool_result",
        "assistant_message",
    ]
    check = next(r for r in said if r["event"] == "tool_result" and r["tool"] == "run_check")
    assert check["passed"] is False and check["exit_code"] == 1 and "1 failed" in check["content"]
    timed = read_jsonl(recorder.trace_path)
    assert [r["event"] for r in timed] == [
        "model_call",
        "skill_load",
        "tool_call",
        "model_call",
        "tool_call",
        "tool_call",
        "model_call",
        "final_response",
        "conversation_turn",
    ]
    assert all(isinstance(r["duration_ms"], int) for r in timed if r["event"] != "skill_load")
    assert {r["trace_id"] for r in timed} == {said[0]["trace_id"]}


def test_follow_ups_see_the_evidence_from_earlier_turns(workspace, tmp_path):
    model = ScriptedModel(
        replies=[calls(call("run_check", "c")), AIMessage(content="1 failed."), AIMessage(content="ok")]
    )
    session, _ = session_for(model, workspace, tmp_path)
    session.ask("Run the check.")
    session.ask("What did it print?")
    assert any(isinstance(m, ToolMessage) and "3 passed, 1 failed" in str(m.content) for m in model.seen[-1])


def test_a_failed_turn_leaves_the_conversation_usable(workspace, tmp_path):
    model = ScriptedModel(replies=[RuntimeError("quota"), AIMessage(content="recovered")])
    session, recorder = session_for(model, workspace, tmp_path)
    with pytest.raises(RuntimeError):
        session.ask("first")
    assert session.messages == []
    assert session.ask("second") == "recovered"
    assert [r["event"] for r in read_jsonl(recorder.conversation_path)][:2] == ["user_message", "error"]


def test_excluded_tools_are_refused_even_if_the_model_names_them(workspace, tmp_path):
    model = ScriptedModel(
        replies=[
            calls(call("write_file", "w", file_path="/codebase/x.md", content="x")),
            AIMessage(content="ok"),
        ]
    )
    session, _ = session_for(model, workspace, tmp_path)
    session.ask("write")
    [refused] = [m for m in session.messages if isinstance(m, ToolMessage)]
    assert refused.status == "error" and "not available to this agent" in refused.content
    assert not (workspace[0] / "x.md").exists()


def test_two_agents_in_one_process_keep_their_own_tool_surfaces(workspace, tmp_path):
    narrow, wide = (
        ScriptedModel(replies=[AIMessage(content="a")]),
        ScriptedModel(replies=[AIMessage(content="b")]),
    )
    session_for(narrow, workspace, tmp_path)[0].ask("hi")
    root, skills = workspace
    graph = assemble(
        wide,
        system_prompt="Another specialist on the same model.",
        tools=[],
        routes={"/codebase/": GitScopedBackend(root)},
        excluded_tools=frozenset({"task"}),
        permissions=[],
    )
    Session(graph, RunRecorder(tmp_path / "other")).ask("hi")
    assert "write_file" not in narrow.offered_tools and "write_file" in wide.offered_tools


def test_history_replayed_by_middleware_is_not_recorded_as_new(workspace, tmp_path):
    model = ScriptedModel(replies=[AIMessage(content="second answer")])
    session, recorder = session_for(model, workspace, tmp_path)
    # A dangling tool call from an earlier turn: Deep Agents patches it by re-emitting history.
    session.messages = [HumanMessage("first"), calls(call("run_check", "old"))]
    events = [e for e in session.stream("again") if e["type"] != "token"]
    assert events == [{"type": "final", "text": "second answer"}]
    timed = read_jsonl(recorder.trace_path)
    assert [r["event"] for r in timed] == ["model_call", "final_response", "conversation_turn"]


def test_a_tool_result_carrying_an_error_is_traced_as_an_error(workspace, tmp_path):
    root, skills = workspace
    broken = StructuredTool.from_function(
        func=lambda: json.dumps({"passed": False, "exit_code": None, "error": "Timed out"}),
        name="run_check",
        description="Run the check.",
    )
    model = ScriptedModel(replies=[calls(call("run_check", "c")), AIMessage(content="inconclusive")])
    recorder = RunRecorder(tmp_path / "runs")
    graph = assemble(
        model,
        system_prompt="x",
        tools=[broken],
        routes={"/codebase/": GitScopedBackend(root)},
        excluded_tools=EXCLUDED,
        permissions=[],
    )
    Session(graph, recorder).ask("check")
    [traced] = [r for r in read_jsonl(recorder.trace_path) if r["event"] == "tool_call"]
    assert traced["status"] == "error"


def test_transient_failures_are_retried_and_a_spent_daily_quota_is_not(workspace, tmp_path, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    model = ScriptedModel(replies=[OVERLOADED, OVERLOADED, AIMessage(content="third time")])
    assert session_for(model, workspace, tmp_path)[0].ask("hi") == "third time"
    per_day = GoogleRateLimitError("429 quotaId GenerateRequestsPerDayPerProjectPerModel-FreeTier")
    model = ScriptedModel(replies=[per_day, AIMessage(content="never reached")])
    with pytest.raises(GoogleRateLimitError):
        session_for(model, workspace, tmp_path)[0].ask("hi")


def test_only_transient_provider_errors_are_retried():
    per_minute = GoogleRateLimitError("429 quotaId GenerateRequestsPerMinutePerProjectPerModel-FreeTier")
    per_day = GoogleRateLimitError("429 quotaId GenerateRequestsPerDayPerProjectPerModel-FreeTier")
    assert transient(per_minute) and transient(OVERLOADED)
    assert not transient(per_day) and not transient(ValueError("bug"))


def test_skill_reads_are_recognised():
    assert skill_read(call("read_file", "x", file_path="/skills/check-things/SKILL.md")) == "check-things"
    assert skill_read(call("read_file", "x", file_path="/codebase/SKILL.md")) is None
    assert skill_read(call("ls", "x", path="/skills/")) is None


def test_text_of_flattens_gemini_content_blocks():
    blocks = [
        {"type": "text", "text": "Hello "},
        {"type": "thinking", "thinking": "hm"},
        {"type": "text", "text": "there"},
    ]
    assert text_of(blocks) == "Hello there" and text_of("plain") == "plain"


def test_result_fields_pick_check_outcomes_out_of_json():
    assert result_fields('{"passed": true, "exit_code": 0, "stdout": "x"}') == {
        "passed": True,
        "exit_code": 0,
    }
    assert result_fields("not json") == {} and result_fields("[1]") == {}


def test_a_turn_ends_within_its_round_budget_with_an_answer(workspace, tmp_path):
    root, skills = workspace
    model = ScriptedModel(
        replies=[
            calls(call("ls", "a", path="/codebase/")),
            calls(call("ls", "b", path="/codebase/")),
            # Like Gemini, the model tries to keep going on its last allowed call.
            AIMessage(content="What I found so far.", tool_calls=[call("ls", "c", path="/codebase/")]),
        ]
    )
    graph = assemble(
        model,
        system_prompt="Explore.",
        tools=[],
        routes={"/codebase/": GitScopedBackend(root)},
        excluded_tools=EXCLUDED,
        permissions=[],
        rounds=3,
    )
    session = Session(graph, RunRecorder(tmp_path / "runs"))
    assert session.ask("look") == "What I found so far."
    assert model.replies == []  # no fourth call was made
    assert model.tool_choices == [None, None, "none"]
    assert FINAL_ROUND.strip() in text_of(model.seen[-1][0].content)
    assert FINAL_ROUND.strip() not in text_of(model.seen[0][0].content)


def test_a_final_reply_with_only_a_tool_call_becomes_a_clear_stop(workspace, tmp_path):
    root, skills = workspace
    model = ScriptedModel(replies=[calls(call("ls", "a", path="/")), calls(call("ls", "b", path="/"))])
    graph = assemble(
        model,
        system_prompt="Explore.",
        tools=[],
        routes={"/codebase/": GitScopedBackend(root)},
        excluded_tools=EXCLUDED,
        permissions=[],
        rounds=2,
    )
    assert Session(graph, RunRecorder(tmp_path / "runs")).ask("look") == STOPPED


def test_a_budget_below_one_round_is_refused():
    with pytest.raises(ValueError, match="at least one model call"):
        RoundBudget(0)
