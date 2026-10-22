"""REPL commands and conversation loading."""

import pytest

from pair_agent.agent import PairAgent, validate_conversation
from pair_agent.cli import _handle_command
from pair_agent.tools import ToolRegistry


def agent() -> PairAgent:
    a = PairAgent(provider=None, registry=ToolRegistry(), system_prompt="SYSTEM")
    a.messages += [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    return a


def test_save_then_load_round_trips(tmp_path, capsys):
    source = agent()
    path = tmp_path / "c.json"
    assert _handle_command(f"/save {path}", source, ToolRegistry())
    target = PairAgent(provider=None, registry=ToolRegistry(), system_prompt="NEW SYSTEM")
    _handle_command(f"/load {path}", target, ToolRegistry())
    assert target.messages == [{"role": "system", "content": "NEW SYSTEM"}, *source.messages[1:]]


def test_save_to_a_missing_folder_reports_instead_of_crashing(tmp_path, capsys):
    assert _handle_command(f"/save {tmp_path / 'nope' / 'c.json'}", agent(), ToolRegistry())
    assert "could not save" in capsys.readouterr().out


@pytest.mark.parametrize("content", ["{not json", '{"role": "user"}', "[1, 2]", '[{"role": "robot"}]'])
def test_bad_files_are_rejected_and_the_conversation_is_kept(tmp_path, capsys, content):
    path = tmp_path / "c.json"
    path.write_text(content, encoding="utf-8")
    a = agent()
    before = list(a.messages)
    assert _handle_command(f"/load {path}", a, ToolRegistry())
    assert "could not load" in capsys.readouterr().out
    assert a.messages == before


def test_a_tool_call_without_its_result_is_rejected():
    with pytest.raises(ValueError, match="without results: x"):
        validate_conversation([
            {"role": "user", "content": "q"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "x", "name": "t", "arguments": {}}]},
            {"role": "user", "content": "next"},
        ])


def test_quit_ends_the_session():
    assert _handle_command("/quit", agent(), ToolRegistry()) is False
