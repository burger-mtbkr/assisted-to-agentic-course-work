"""Settings, from `doctor-agent/.env` and the environment (the environment wins)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ConfigError(Exception):
    """A setting is missing or points somewhere that does not exist."""


def _positive_int(name: str, value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise ConfigError(f"{name} must be a whole number of seconds, not {value!r}.") from None
    if number <= 0:
        raise ConfigError(f"{name} must be more than zero.")
    return number


@dataclass(frozen=True)
class DoctorConfig:
    codebase_path: Path
    test_command: str
    lint_command: str
    command_timeout_seconds: int
    model: str
    api_key: str
    runs_dir: Path
    skills_dir: Path

    @classmethod
    def load(cls, project_root: Path = PROJECT_ROOT) -> DoctorConfig:
        # dotenv_values, not load_dotenv: the key must not reach os.environ, which
        # the checks' subprocesses (npm, dotnet) inherit.
        settings = {**dotenv_values(project_root / ".env"), **os.environ}

        def get(name: str, default: str) -> str:
            return (settings.get(name) or default).strip()

        def path(name: str, default: str) -> Path:
            value = Path(get(name, default)).expanduser()
            return (value if value.is_absolute() else project_root / value).resolve()

        codebase = path("DOCTOR_CODEBASE_PATH", "../config-service")
        if not codebase.is_dir():
            raise ConfigError(
                f"Codebase not found at {codebase}. Set DOCTOR_CODEBASE_PATH to the directory to diagnose."
            )
        api_key = get("GEMINI_API_KEY", "")
        if not api_key:
            raise ConfigError("GEMINI_API_KEY is not set: copy .env.example to .env and add the key.")
        return cls(
            codebase_path=codebase,
            test_command=get("DOCTOR_TEST_COMMAND", "npm run test"),
            lint_command=get("DOCTOR_LINT_COMMAND", "npm run lint"),
            command_timeout_seconds=_positive_int(
                "DOCTOR_COMMAND_TIMEOUT", get("DOCTOR_COMMAND_TIMEOUT", "300")
            ),
            model=get("GEMINI_MODEL", "gemini-flash-latest"),
            api_key=api_key,
            runs_dir=path("DOCTOR_RUNS_DIR", ".doctor-runs"),
            skills_dir=project_root / "skills",
        )
