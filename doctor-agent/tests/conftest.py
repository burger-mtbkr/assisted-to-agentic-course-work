import json
import subprocess
import sys
from pathlib import Path

import pytest

from doctor_agent.config import DoctorConfig

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def py(code: str) -> str:
    """A shell command running `code` with this interpreter: a harmless fixture check."""
    return f'"{sys.executable}" -c "{code}"'


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


@pytest.fixture
def codebase(tmp_path):
    root = tmp_path / "codebase"
    (root / "src").mkdir(parents=True)
    (root / "README.md").write_text("# Patient\n", encoding="utf-8")
    (root / "src" / "App.cs").write_text("class App {}\n", encoding="utf-8")
    (root / ".gitignore").write_text(".env\n", encoding="utf-8")
    (root / ".env").write_text("AWS_SECRET_ACCESS_KEY=hunter2\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


@pytest.fixture
def config(codebase, tmp_path):
    return DoctorConfig(
        codebase_path=codebase,
        test_command=py("print('3 passed')"),
        lint_command=py("import sys; print('rule CS0168 in src/App.cs:1'); sys.exit(1)"),
        command_timeout_seconds=60,
        model="scripted-doctor",
        api_key="unused",
        runs_dir=tmp_path / "runs",
        skills_dir=PROJECT_ROOT / "skills",
    )
