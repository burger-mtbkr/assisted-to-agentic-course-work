"""The terminal front end: the interactive loop over a shared runtime.

Commands: /tools, /messages, /save PATH, /load PATH, /reset, /quit.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from pair_agent.agent import PairAgent, validate_conversation
from pair_agent.provider import ProviderError
from pair_agent.runtime import StartupError, configure_process, open_runtime
from pair_agent.tools import ToolRegistry


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
    try:
        async with open_runtime() as runtime:
            agent = runtime.new_agent(on_event=_print_event)
            for line in runtime.banner():
                print(line)
            print("  /help for commands")

            while True:
                try:
                    line = (await asyncio.to_thread(input, "\nyou> ")).strip()
                except EOFError:
                    break
                if not line:
                    continue
                if line.startswith("/"):
                    if not _handle_command(line, agent, runtime.registry):
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
            usage = runtime.provider.usage
            print(f"\n[session tokens: {usage.input_tokens} in, {usage.output_tokens} out]")
            return 0
    except StartupError as exc:
        print(exc, file=sys.stderr)
        return 2


def main() -> None:
    configure_process()
    sys.exit(asyncio.run(run()))
