"""Settings: defaults, overrides, clear startup errors, and the key kept out of os.environ."""

import os

import pytest

from doctor_agent.config import ConfigError, DoctorConfig


@pytest.fixture
def project(tmp_path, monkeypatch):
    for name in [n for n in os.environ if n.startswith(("DOCTOR_", "GEMINI_"))]:
        monkeypatch.delenv(name)
    root = tmp_path / "doctor-agent"
    root.mkdir()
    (tmp_path / "config-service").mkdir()
    (root / ".env").write_text("GEMINI_API_KEY=from-dotenv\n", encoding="utf-8")
    return root


def test_defaults_resolve_next_to_the_project(project):
    config = DoctorConfig.load(project)
    assert config.codebase_path == (project.parent / "config-service").resolve()
    assert config.test_command == "npm run test" and config.lint_command == "npm run lint"
    assert config.model == "gemini-flash-latest" and config.runs_dir == (project / ".doctor-runs").resolve()


def test_the_key_is_read_without_entering_the_environment(project):
    assert DoctorConfig.load(project).api_key == "from-dotenv"
    assert "GEMINI_API_KEY" not in os.environ  # the checks' subprocesses inherit os.environ


def test_the_environment_overrides_dotenv(project, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "from-env")
    monkeypatch.setenv("DOCTOR_TEST_COMMAND", "make test")
    config = DoctorConfig.load(project)
    assert config.api_key == "from-env" and config.test_command == "make test"


def test_a_missing_codebase_fails_at_startup(project, monkeypatch):
    monkeypatch.setenv("DOCTOR_CODEBASE_PATH", "../nowhere")
    with pytest.raises(ConfigError, match="Codebase not found"):
        DoctorConfig.load(project)


def test_a_missing_key_fails_at_startup(project):
    (project / ".env").write_text("", encoding="utf-8")
    with pytest.raises(ConfigError, match="GEMINI_API_KEY"):
        DoctorConfig.load(project)


@pytest.mark.parametrize("value", ["soon", "0", "-5"])
def test_a_bad_timeout_fails_at_startup(project, monkeypatch, value):
    monkeypatch.setenv("DOCTOR_COMMAND_TIMEOUT", value)
    with pytest.raises(ConfigError, match="DOCTOR_COMMAND_TIMEOUT"):
        DoctorConfig.load(project)
