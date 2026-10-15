"""Skill discovery and progressive disclosure.

At startup only each SKILL.md's frontmatter is read. The body is loaded when
the model calls activate_skill(name), and a bundled script runs only when the
model calls run_skill_script(name, args).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

from pair_agent.tools import ToolError, ToolOutcome


@dataclass(frozen=True)
class SkillMetadata:
    name: str
    description: str
    directory: Path


def read_frontmatter(skill_file: Path) -> dict:
    """Parse only the YAML block between the leading `---` lines.

    Real-world skills often have an unquoted colon inside `description:`, which
    is invalid YAML but accepted by other harnesses, so fall back to reading each
    top-level `key: value` line literally rather than dropping the skill.
    """
    with skill_file.open(encoding="utf-8") as handle:
        if handle.readline().strip() != "---":
            return {}
        block = []
        for line in handle:
            if line.strip() == "---":
                break
            block.append(line)
        else:
            return {}
    try:
        parsed = yaml.safe_load("".join(block))
        return parsed if isinstance(parsed, dict) else {}
    except yaml.YAMLError:
        fields = {}
        for line in block:
            key, sep, value = line.partition(":")
            if sep and not line.startswith((" ", "\t")):
                fields[key.strip()] = value.strip()
        return fields


def find_bash() -> str:
    """Git Bash, never WSL's launcher.

    On Windows, CreateProcess searches System32 before PATH, so a bare
    "bash" runs C:\\Windows\\System32\\bash.exe (WSL) instead of Git Bash.
    """
    configured = os.environ.get("PAIR_AGENT_BASH")
    if configured:
        return configured
    system32 = Path(os.environ.get("SystemRoot", r"C:\Windows"), "System32").resolve()
    for directory in filter(None, os.environ.get("PATH", "").split(os.pathsep)):
        resolved = Path(directory).resolve()
        if resolved == system32 or "windowsapps" in (part.lower() for part in resolved.parts):
            continue
        found = shutil.which("bash", path=directory)
        if found:
            return found
    git_bash = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "bin" / "bash.exe"
    if git_bash.is_file():
        return str(git_bash)
    raise ToolError("No bash found for skill scripts. Install Git Bash or set PAIR_AGENT_BASH.")


class SkillCatalog:
    def __init__(self, skills_dir: Path, work_dir: Path, script_timeout: float = 600):
        self.skills_dir = skills_dir
        self.work_dir = work_dir
        self.script_timeout = script_timeout
        self._skills: dict[str, SkillMetadata] = {}
        self._activated: set[str] = set()
        if skills_dir.is_dir():
            for candidate in sorted(skills_dir.iterdir()):
                skill_file = candidate / "SKILL.md"
                if not skill_file.is_file():  # e.g. _lib/, shared helpers with no SKILL.md
                    continue
                meta = read_frontmatter(skill_file)
                name = meta.get("name") or candidate.name
                self._skills[name] = SkillMetadata(name, meta.get("description", ""), candidate.resolve())

    def names(self) -> list[str]:
        return list(self._skills)

    def list_skills(self) -> list[dict]:
        return [
            {"name": s.name, "description": s.description, "location": str(s.directory)}
            for s in self._skills.values()
        ]

    def _get(self, name: str) -> SkillMetadata:
        if name not in self._skills:
            raise ToolError(f"Unknown skill '{name}'. Known skills: {', '.join(self._skills) or 'none'}")
        return self._skills[name]

    def activate_skill(self, name: str) -> dict:
        skill = self._get(name)
        self._activated.add(name)
        return {
            "name": skill.name,
            "base_directory": str(skill.directory),
            "bundled_files": sorted(
                str(p.relative_to(skill.directory)).replace("\\", "/")
                for p in skill.directory.rglob("*")
                if p.is_file() and p.name != "SKILL.md"
            ),
            "instructions": (skill.directory / "SKILL.md").read_text(encoding="utf-8"),
        }

    def _check_args(self, args: object) -> list[str]:
        """Model-supplied arguments must not move the script outside the code directory:
        the harness pins the project, and any path-like value must resolve inside it."""
        if args is None:
            return []
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            raise ToolError("args must be a list of strings, e.g. [\"--work-item\", \"002\"]")
        root = self.work_dir.resolve()
        for arg in args:
            if arg == "--project-dir" or arg.startswith("--project-dir="):
                raise ToolError(f"--project-dir is not allowed: the harness runs skills in {root}")
            if not arg.startswith("-") and not (root / arg).resolve().is_relative_to(root):
                raise ToolError(f"argument '{arg}' points outside the code directory {root}")
        return args

    def run_skill_script(self, name: str, args: list[str] | None = None) -> ToolOutcome:
        skill = self._get(name)
        if name not in self._activated:
            raise ToolError(f"Activate the skill first: call activate_skill('{name}') and follow its instructions.")
        script = skill.directory / "script.sh"
        if not script.is_file():
            raise ToolError(f"Skill '{name}' has no script.sh")
        checked = self._check_args(args)
        try:
            proc = subprocess.run(
                [find_bash(), script.as_posix(), *checked],
                cwd=self.work_dir, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                encoding="utf-8", errors="replace", timeout=self.script_timeout,
            )
        except subprocess.TimeoutExpired:
            raise ToolError(f"{name}/script.sh did not finish in {self.script_timeout:g}s") from None
        output = proc.stdout
        if proc.stderr.strip():
            output += f"\n=== STDERR ===\n{proc.stderr}"
        return ToolOutcome(f"exit code {proc.returncode}\n{output}", proc.returncode != 0)
