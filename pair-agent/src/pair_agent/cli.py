"""Startup wiring and the interactive loop.

Commands: /tools, /messages, /save PATH, /load PATH, /reset, /quit.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
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


def _env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).resolve() if value else default


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


def _print_event(kind: str, data: dict) -> None:
    if kind == "tool_call":
        print(f"  -> {data['name']}({json.dumps(data['arguments'], ensure_ascii=False)})")
    elif kind == "tool_result":
        status = "error" if data["is_error"] else "ok"
        print(f"  <- {data['name']}: {status}, {data['chars']} chars")


def _summarise(message: dict) -> str:
    role = message["role"]
    if role == "tool":
        flag = " ERROR" if message.get("is_error") else ""
        return f"tool[{message['name']}]{flag}: {len(message['content'])} chars"
    calls = ", ".join(c["name"] for c in message.get("tool_calls", []))
    text = message.get("content", "").replace("\n", " ")
    preview = text[:100] + ("..." if len(text) > 100 else "")
    return f"{role}: {preview}" + (f"  [calls: {calls}]" if calls else "")


def validate_conversation(loaded: object) -> list[dict]:
    """A saved conversation, minus its system prompt, checked so that a bad file cannot
    leave the array in a state the provider will reject on every later turn."""
    if not isinstance(loaded, list) or not all(isinstance(m, dict) for m in loaded):
        raise ValueError("expected a JSON list of message objects")
    messages = [m for m in loaded if m.get("role") != "system"]
    pending: set[str] = set()
    for message in messages:
        role = message.get("role")
        if role not in ("user", "assistant", "tool") or not isinstance(message.get("content", ""), str):
            raise ValueError(f"unexpected message: {str(message)[:80]}")
        if role == "tool":
            pending.discard(message.get("tool_call_id"))
            continue
        if pending:
            raise ValueError(f"tool call(s) without results: {', '.join(sorted(pending))}")
        pending = {call["id"] for call in message.get("tool_calls", [])}
    if pending:
        raise ValueError(f"tool call(s) without results: {', '.join(sorted(pending))}")
    return messages


def _handle_command(line: str, agent: PairAgent, registry: ToolRegistry) -> bool:
    """Run a /command. Returns False when the session should end."""
    command, _, arg = line.partition(" ")
    if command == "/quit":
        return False
    if command == "/tools":
        for tool in registry.all():
            print(f"  [{tool.source}] {tool.name}")
    elif command == "/messages":
        for index, message in enumerate(agent.messages):
            print(f"  {index:>3} {_summarise(message)}")
    elif command == "/save" and arg:
        try:
            Path(arg).write_text(json.dumps(agent.messages, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  saved {len(agent.messages)} messages to {arg}")
        except OSError as exc:
            print(f"  could not save: {exc}")
    elif command == "/load" and arg:
        try:
            loaded = validate_conversation(json.loads(Path(arg).read_text(encoding="utf-8")))
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            print(f"  could not load: {type(exc).__name__}: {exc}")
        else:
            agent.messages = agent.messages[:1] + loaded
            print(f"  loaded {len(loaded)} messages (current system prompt kept)")
    elif command == "/reset":
        agent.reset()
        print("  conversation cleared")
    else:
        print("  commands: /tools /messages /save PATH /load PATH /reset /quit")
    return True


async def run() -> int:
    code_dir = _env_path("PAIR_AGENT_CODE_DIR", REPO_ROOT / "config-service")
    skills_dir = _env_path("PAIR_AGENT_SKILLS_DIR", REPO_ROOT / ".claude" / "skills")
    mcp_config = _env_path("PAIR_AGENT_MCP_CONFIG", PACKAGE_ROOT / "mcp.json")

    if not code_dir.is_dir():
        print(f"[config error] code directory not found: {code_dir} (PAIR_AGENT_CODE_DIR)", file=sys.stderr)
        return 2
    skills = SkillCatalog(skills_dir, code_dir)
    if not skills.names():
        print(f"[warning] no skills found in {skills_dir} (PAIR_AGENT_SKILLS_DIR)", file=sys.stderr)
    registry = ToolRegistry()
    for tool in harness_tools(RepoTools(code_dir), skills):
        registry.register(tool)
    try:
        provider = GeminiProvider.from_env()
    except ProviderError as exc:
        print(f"[provider error] {exc}", file=sys.stderr)
        return 2

    mcp = McpConnections()
    try:
        await mcp.start(mcp_config)
        for tool in mcp.tools:
            registry.register(tool)

        agent = PairAgent(
            provider,
            registry,
            build_system_prompt(code_dir, skills.list_skills(), mcp.instructions),
            max_tool_rounds=int(os.environ.get("PAIR_AGENT_MAX_TOOL_ROUNDS", "12")),
            on_event=_print_event,
        )
        print(f"PAIR Agent - {provider.model} - code: {code_dir}")
        print(f"  {len(skills.names())} skills ({', '.join(skills.names())}), "
              f"{len(mcp.tools)} MCP tools from {mcp_config.name}, {len(registry.all())} tools total")
        print("  /help for commands")

        while True:
            try:
                line = (await asyncio.to_thread(input, "\nyou> ")).strip()
            except EOFError:
                break
            if not line:
                continue
            if line.startswith("/"):
                if not _handle_command(line, agent, registry):
                    break
                continue
            try:
                answer = await agent.send(line)
            except ProviderError as exc:
                print(f"\n[provider error] {exc}")
                continue
            except Exception as exc:  # the turn was rolled back; keep the session alive
                print(f"\n[harness error] {type(exc).__name__}: {exc}")
                continue
            print(f"\nagent> {answer}")
        usage = provider.usage
        print(f"\n[session tokens: {usage.input_tokens} in, {usage.output_tokens} out]")
        return 0
    except McpConfigError as exc:
        print(f"[mcp error] {exc}", file=sys.stderr)
        return 2
    finally:
        await mcp.close()
        await provider.close()


def main() -> None:
    # Windows consoles and pipes default to cp1252, which cannot encode what models write.
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    load_dotenv(PACKAGE_ROOT / ".env")  # GEMINI_API_KEY lives here, git-ignored
    sys.exit(asyncio.run(run()))
