"""Startup wiring shared by the terminal and browser front ends: settings, tools, provider, MCP."""

from __future__ import annotations

import os
import sys
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from pair_agent.agent import PairAgent
from pair_agent.mcp_client import McpConfigError, McpConnections
from pair_agent.prompt import build_system_prompt
from pair_agent.provider import GeminiProvider, ProviderError
from pair_agent.skills import SkillCatalog
from pair_agent.tools import RepoTools, Tool, ToolRegistry

PACKAGE_ROOT = Path(__file__).resolve().parents[2]  # pair-agent/
REPO_ROOT = PACKAGE_ROOT.parent


class StartupError(Exception):
    """A setting or dependency is wrong; the message says which and how to fix it."""


def env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).resolve() if value else default


def configure_process() -> None:
    # Windows consoles and pipes default to cp1252, which cannot encode what models write.
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    load_dotenv(PACKAGE_ROOT / ".env")  # GEMINI_API_KEY lives here, git-ignored


def harness_tools(repo: RepoTools, skills: SkillCatalog) -> list[Tool]:
    skill_name = {"type": "string", "description": "Exact skill name from the catalog."}
    if skills.names():
        skill_name["enum"] = skills.names()
    return [
        Tool(
            "read_file",
            "Read a text file from the repository by path relative to the code directory, with line "
            "numbers. Use to inspect a specific file you already know the path of (from lookup_term's "
            "source_files, search_code, or a skill's output).",
            {"type": "object", "properties": {
                "path": {"type": "string", "description": "Path relative to the code directory."},
                "start_line": {"type": "integer", "minimum": 1, "default": 1},
                "end_line": {"type": "integer", "minimum": 1, "default": 200},
            }, "required": ["path"]},
            repo.read_file, "harness",
        ),
        Tool(
            "search_code",
            "Case-insensitive fixed-string search over the repository's tracked files (git grep). "
            "Returns path:line:text matches. Use to find where an identifier or string appears when "
            "you do not know the file.",
            {"type": "object", "properties": {
                "query": {"type": "string", "minLength": 1},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 100, "default": 30},
            }, "required": ["query"]},
            repo.search_code, "harness",
        ),
        Tool(
            "list_skills",
            "List the procedural skills available in this harness (name and description only). Use when "
            "a request sounds like a workflow - starting, resuming, or finishing a piece of work.",
            {"type": "object", "properties": {}},
            skills.list_skills, "harness",
        ),
        Tool(
            "activate_skill",
            "Load one skill's full instructions (SKILL.md), its base directory, and its bundled files. "
            "If the user's request matches one of the skills below, call this FIRST - before reading "
            "files or calling any other tool - and then follow the loaded instructions.\n\nSkills:\n"
            + "\n".join(f"- {s['name']}: {s['description']}" for s in skills.list_skills()),
            {"type": "object", "properties": {"name": skill_name}, "required": ["name"]},
            skills.activate_skill, "harness",
        ),
        Tool(
            "run_skill_script",
            "Run an activated skill's bundled script.sh in the code directory and return its output. "
            "Use when the skill's instructions say to run its script; pass the script's arguments.",
            {"type": "object", "properties": {
                "name": skill_name,
                "args": {"type": "array", "items": {"type": "string"}, "default": []},
            }, "required": ["name"]},
            skills.run_skill_script, "harness",
        ),
    ]


@dataclass
class Runtime:
    """Everything a conversation needs, started once and shared by every agent built from it."""

    provider: GeminiProvider
    registry: ToolRegistry
    code_dir: Path
    mcp_config: Path
    skills: list[dict]
    mcp_tool_count: int
    system_prompt: str
    max_tool_rounds: int

    def new_agent(self, on_event: Callable[[str, dict], None] | None = None) -> PairAgent:
        return PairAgent(self.provider, self.registry, self.system_prompt, self.max_tool_rounds, on_event)

    def banner(self) -> list[str]:
        names = ", ".join(s["name"] for s in self.skills)
        return [
            f"PAIR Agent - {self.provider.model} - code: {self.code_dir}",
            f"  {len(self.skills)} skills ({names}), {self.mcp_tool_count} MCP tools from "
            f"{self.mcp_config.name}, {len(self.registry.all())} tools total",
        ]


@asynccontextmanager
async def open_runtime(provider_settings: Mapping[str, str | None] = os.environ) -> AsyncIterator[Runtime]:
    """Read the settings, register the tools, connect the provider and the MCP servers.

    `provider_settings` holds GEMINI_API_KEY and GEMINI_MODEL. A host that also runs other
    agents passes them here rather than loading pair-agent/.env into the environment
    every subprocess inherits.
    """
    code_dir = env_path("PAIR_AGENT_CODE_DIR", REPO_ROOT / "config-service")
    skills_dir = env_path("PAIR_AGENT_SKILLS_DIR", REPO_ROOT / ".claude" / "skills")
    mcp_config = env_path("PAIR_AGENT_MCP_CONFIG", PACKAGE_ROOT / "mcp.json")

    if not code_dir.is_dir():
        raise StartupError(f"[config error] code directory not found: {code_dir} (PAIR_AGENT_CODE_DIR)")
    skills = SkillCatalog(skills_dir, code_dir)
    if not skills.names():
        print(f"[warning] no skills found in {skills_dir} (PAIR_AGENT_SKILLS_DIR)", file=sys.stderr)
    registry = ToolRegistry()
    for tool in harness_tools(RepoTools(code_dir), skills):
        registry.register(tool)
    try:
        provider = GeminiProvider.from_env(provider_settings)
    except ProviderError as exc:
        raise StartupError(f"[provider error] {exc}") from exc

    mcp = McpConnections()
    try:
        try:
            await mcp.start(mcp_config)
        except McpConfigError as exc:
            raise StartupError(f"[mcp error] {exc}") from exc
        for tool in mcp.tools:
            registry.register(tool)
        yield Runtime(
            provider=provider,
            registry=registry,
            code_dir=code_dir,
            mcp_config=mcp_config,
            skills=skills.list_skills(),
            mcp_tool_count=len(mcp.tools),
            system_prompt=build_system_prompt(code_dir, skills.list_skills(), mcp.instructions),
            max_tool_rounds=int(os.environ.get("PAIR_AGENT_MAX_TOOL_ROUNDS", "12")),
        )
    finally:
        await mcp.close()
        await provider.close()
