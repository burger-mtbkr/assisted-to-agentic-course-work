"""`doctor`: talk to the Doctor. A REPL by default; `--ask` scripts a conversation."""

from __future__ import annotations

import argparse
import sys

from agent_kit.console import converse
from agent_kit.recording import RunRecorder

from doctor_agent.agent import DoctorAgent
from doctor_agent.config import ConfigError, DoctorConfig


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="doctor", description="The Doctor: codebase-health diagnosis.")
    parser.add_argument(
        "--ask",
        action="append",
        metavar="MESSAGE",
        help="send MESSAGE and exit; repeat for a multi-turn conversation",
    )
    args = parser.parse_args(argv)
    try:
        config = DoctorConfig.load()
    except ConfigError as exc:
        print(f"doctor: {exc}", file=sys.stderr)
        return 2
    print(f"Doctor ({config.model}) diagnosing {config.codebase_path}")
    print(f"Recording to {config.runs_dir}\n")
    return converse("Doctor", lambda: DoctorAgent(config, RunRecorder(config.runs_dir)), args.ask)


if __name__ == "__main__":
    sys.exit(main())
