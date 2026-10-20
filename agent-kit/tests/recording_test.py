"""The recorder writes one JSONL record per event; compaction keeps both ends."""

import json
from pathlib import Path

from agent_kit.recording import OUTPUT_LIMIT, TRUNCATION_MARKER, RunRecorder, compact


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_events_land_in_the_session_files(tmp_path):
    recorder = RunRecorder(tmp_path, session_id="s1")
    recorder.conversation("user_message", content="Is it healthy?")
    recorder.trace("tool_call", "t1", tool="run_tests", duration_ms=12, status="ok")
    assert recorder.conversation_path == tmp_path / "conversations" / "conversation_s1.jsonl"
    assert recorder.trace_path == tmp_path / "traces" / "trace_s1.jsonl"
    [said] = read_jsonl(recorder.conversation_path)
    [timed] = read_jsonl(recorder.trace_path)
    assert said["event"] == "user_message" and said["conversation_id"] == "s1"
    assert said["content"] == "Is it healthy?" and said["timestamp"]
    assert timed == {**timed, "event": "tool_call", "trace_id": "t1", "tool": "run_tests", "duration_ms": 12}


def test_records_append_and_tolerate_non_json_values(tmp_path):
    recorder = RunRecorder(tmp_path)
    recorder.conversation("tool_call", arguments={"path": Path("src/App.cs")})
    recorder.conversation("assistant_message", content="ok")
    records = read_jsonl(recorder.conversation_path)
    assert [r["event"] for r in records] == ["tool_call", "assistant_message"]
    assert records[0]["arguments"] == {"path": str(Path("src/App.cs"))}


def test_each_session_gets_its_own_files(tmp_path):
    assert RunRecorder(tmp_path).conversation_path != RunRecorder(tmp_path).conversation_path


def test_compact_keeps_short_output_and_both_ends_of_long_output():
    assert compact("  short  ") == "short"
    long = "HEAD-" + "x" * (OUTPUT_LIMIT * 2) + "-FAILED: 2 tests"
    kept = compact(long)
    assert len(kept) == OUTPUT_LIMIT and TRUNCATION_MARKER in kept
    assert kept.startswith("HEAD-") and kept.endswith("-FAILED: 2 tests")
    assert len(compact(long, 100)) == 100
