"""The assembled Doctor, driven by a scripted model: tool surface, identity, boundaries.

How a session records turns is agent-kit's and tested there; this is what is the Doctor's.
"""

from agent_kit.harness import text_of
from agent_kit.recording import RunRecorder
from agent_kit.testing import ScriptedModel, call, calls
from conftest import read_jsonl
from langchain_core.messages import AIMessage, ToolMessage

from doctor_agent.agent import DoctorAgent


def doctor(config, *replies):
    model = ScriptedModel(replies=list(replies))
    recorder = RunRecorder(config.runs_dir)
    return DoctorAgent(config, recorder, model=model), model, recorder


def tool_messages(agent: DoctorAgent) -> dict[str, ToolMessage]:
    return {m.tool_call_id: m for m in agent.messages if isinstance(m, ToolMessage)}


def test_the_doctor_is_offered_read_and_check_tools_only(config):
    agent, model, _ = doctor(config, AIMessage(content="I diagnose; I do not edit."))
    assert agent.ask("What do you do?") == "I diagnose; I do not edit."
    assert model.offered_tools == ["glob", "grep", "ls", "read_file", "run_lint", "run_tests"]


def test_the_system_prompt_carries_the_identity_and_the_skill_catalog(config):
    agent, model, _ = doctor(config, AIMessage(content="ok"))
    agent.ask("hi")
    system = text_of(model.seen[0][0].content)
    assert "You are the Doctor" in system and "never edit" in system
    assert "triage-codebase-health" in system  # the skill's metadata, not its body
    assert "Healthy** - every check ran" not in system


def test_secrets_ignored_files_and_paths_outside_the_mount_are_unreadable(config):
    (config.codebase_path.parent / "outside.txt").write_text("outside\n", encoding="utf-8")
    agent, _, _ = doctor(
        config,
        calls(
            call("read_file", "env", file_path="/codebase/.env"),
            call("read_file", "outside", file_path="/codebase/../outside.txt"),
            call("read_file", "host", file_path="/outside.txt"),
            call("grep", "grep", pattern="AWS_SECRET", path="/codebase/"),
            call("read_file", "readme", file_path="/codebase/README.md"),
        ),
        AIMessage(content="done"),
    )
    agent.ask("look around")
    results = tool_messages(agent)
    assert "hunter2" not in results["env"].content and "git ignores it" in results["env"].content
    assert "outside\n" not in results["outside"].content and "outside\n" not in results["host"].content
    assert "hunter2" not in results["grep"].content and ".env" not in results["grep"].content
    assert "# Patient" in results["readme"].content


def test_writes_are_refused_even_when_the_model_asks(config):
    agent, _, _ = doctor(
        config,
        calls(
            call("write_file", "w", file_path="/codebase/NEW.md", content="x"),
            call("edit_file", "e", file_path="/codebase/README.md", old_string="Patient", new_string="Fixed"),
        ),
        AIMessage(content="done"),
    )
    agent.ask("fix it")
    results = tool_messages(agent)
    assert all(results[i].status == "error" or "Error" in str(results[i].content) for i in ("w", "e"))
    assert not (config.codebase_path / "NEW.md").exists()
    assert (config.codebase_path / "README.md").read_text(encoding="utf-8") == "# Patient\n"


def test_a_diagnosis_runs_the_real_checks_and_records_skill_use(config):
    agent, _, recorder = doctor(
        config,
        calls(call("read_file", "skill", file_path="/skills/triage-codebase-health/SKILL.md")),
        calls(call("run_tests", "t"), call("run_lint", "l")),
        calls(call("read_file", "f", file_path="/codebase/src/App.cs")),
        AIMessage(content="## Health Report\n**Status:** Unhealthy"),
    )
    assert agent.ask("Is the codebase healthy?").startswith("## Health Report")
    results = tool_messages(agent)
    assert "Triage codebase health" in results["skill"].content
    assert '"passed": true' in results["t"].content and '"passed": false' in results["l"].content
    said = read_jsonl(recorder.conversation_path)
    assert {"event": "skill_read", "skill": "triage-codebase-health"}.items() <= said[2].items()
    lint = next(r for r in said if r["event"] == "tool_result" and r["tool"] == "run_lint")
    assert lint["passed"] is False and lint["exit_code"] == 1 and "CS0168" in lint["content"]
