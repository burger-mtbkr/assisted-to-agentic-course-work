"""The terminal side of a Session: stream a turn, or hold a conversation."""

from __future__ import annotations

import sys
from collections.abc import Callable

from agent_kit.harness import Session

HELP = "/artifacts shows where this session is recorded, /reset starts a new conversation, /quit exits."


def describe(event: dict) -> str:
    if event["type"] == "tool_call":
        args = ", ".join(f"{k}={v!r}" for k, v in event["args"].items())
        return f"  -> {event['name']}({args})"
    detail = f"passed={event['passed']}, exit_code={event.get('exit_code')}" if "passed" in event else ""
    return f"  <- {event['name']}: {event['status']}" + (f" ({detail})" if detail else "")


def run_turn(session: Session, message: str) -> None:
    streamed = False
    for event in session.stream(message):
        if event["type"] == "token":
            print(event["text"], end="", flush=True)
            streamed = True
        elif event["type"] in ("tool_call", "tool_result"):
            print(("\n" if streamed else "") + describe(event), flush=True)
            streamed = False
        elif not streamed:  # final, when the provider did not stream the text
            print(event["text"], end="")
    print("\n")


def _artifacts(session: Session) -> str:
    return f"Conversation: {session.recorder.conversation_path}\nTrace: {session.recorder.trace_path}"


def converse(name: str, new_session: Callable[[], Session], asks: list[str] | None = None) -> int:
    """`asks` scripts a conversation and exits (1 if a turn failed); otherwise a REPL."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    session = new_session()
    if asks:
        for message in asks:
            print(f"You: {message}\n{name}: ", end="", flush=True)
            try:
                run_turn(session, message)
            except (Exception, KeyboardInterrupt) as exc:
                print(f"\n[turn failed: {type(exc).__name__}: {exc}]\n")
                print(_artifacts(session))
                return 1
        print(_artifacts(session))
        return 0

    print(HELP)
    while True:
        try:
            message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not message:
            continue
        if message == "/quit":
            return 0
        if message == "/reset":
            session = new_session()
            print("New conversation.\n")
            continue
        if message == "/artifacts":
            print(_artifacts(session) + "\n")
            continue
        print(f"{name}: ", end="", flush=True)
        try:
            run_turn(session, message)
        except (Exception, KeyboardInterrupt) as exc:  # a failed or interrupted turn must not end the session
            print(f"\n[turn failed: {type(exc).__name__}: {exc}]\n")
