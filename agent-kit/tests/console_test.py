"""The terminal side: tool progress lines, scripted conversations, and failures that do not kill the REPL."""

from types import SimpleNamespace

import pytest

from agent_kit.console import converse, describe


class FakeSession:
    def __init__(self, replies):
        self.replies = list(replies)
        self.recorder = SimpleNamespace(conversation_path="conv.jsonl", trace_path="trace.jsonl")

    def stream(self, message):
        reply = self.replies.pop(0)
        if isinstance(reply, BaseException):
            raise reply
        yield {"type": "tool_call", "name": "run_tests", "args": {}}
        yield {"type": "tool_result", "name": "run_tests", "status": "ok", "passed": False, "exit_code": 1}
        yield {"type": "token", "text": reply}
        yield {"type": "final", "text": reply}


def test_describe_shows_calls_and_check_outcomes():
    assert describe({"type": "tool_call", "name": "read_file", "args": {"file_path": "/codebase/a"}}) == (
        "  -> read_file(file_path='/codebase/a')"
    )
    assert describe(
        {"type": "tool_result", "name": "run_tests", "status": "ok", "passed": True, "exit_code": 0}
    ) == ("  <- run_tests: ok (passed=True, exit_code=0)")
    assert describe({"type": "tool_result", "name": "ls", "status": "error"}) == "  <- ls: error"


def test_a_scripted_conversation_prints_every_turn_and_the_artifacts(capsys):
    assert (
        converse("Doctor", lambda: FakeSession(["Healthy.", "Nothing failed."]), ["Healthy?", "What failed?"])
        == 0
    )
    out = capsys.readouterr().out
    assert "You: Healthy?\nDoctor: " in out and "-> run_tests()" in out
    assert "<- run_tests: ok (passed=False, exit_code=1)" in out and "Nothing failed." in out
    assert out.rstrip().endswith("Trace: trace.jsonl")


@pytest.mark.parametrize("failure", [RuntimeError("quota"), KeyboardInterrupt()])
def test_a_failed_scripted_turn_stops_with_status_1(capsys, failure):
    assert converse("Doctor", lambda: FakeSession([failure, "never"]), ["first", "second"]) == 1
    out = capsys.readouterr().out
    assert "[turn failed:" in out and "You: second" not in out


def test_the_repl_survives_a_failed_turn_and_handles_commands(capsys, monkeypatch):
    typed = iter(["first", "/artifacts", "/reset", "", "second", "/quit"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(typed))
    sessions = []

    def new_session():
        sessions.append(FakeSession([RuntimeError("503"), "after"] if not sessions else ["fresh"]))
        return sessions[-1]

    assert converse("Doctor", new_session) == 0
    out = capsys.readouterr().out
    assert "[turn failed: RuntimeError: 503]" in out and "Conversation: conv.jsonl" in out
    assert "New conversation." in out and "fresh" in out and len(sessions) == 2
