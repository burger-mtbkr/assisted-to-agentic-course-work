"""`codebase-team`: run the team, stop at the approval gate, and look at what happened.

run [--scenario S]                     diagnose and brief, then stop for approval (the safe path)
run ... --approve PATH --rationale R   the full approved path in one command
approve TASK --path P --rationale R    record the human decision (--reject to refuse;
                                       --allow-tests lets the Mechanic run the tests)
continue TASK [--mechanic agent|human] patch (only if approved), verify, [--remember]
evals TASK | inspect TASK | list
"""

from __future__ import annotations

import argparse
import sys

from agent_kit.harness import gemini
from librarian_agent.agent import build_embedder, build_tools
from librarian_agent.config import ConfigError, LibrarianConfig

from codebase_team.doctor import DoctorAdapter
from codebase_team.evals import evaluate
from codebase_team.inspection import report
from codebase_team.librarian import LibrarianAdapter
from codebase_team.mechanic import TESTS_COMMAND, AgentMechanic, HumanMechanic
from codebase_team.orchestrator import Team, TeamConfig
from codebase_team.scenarios import SCENARIOS
from codebase_team.workspace import Run, load_run


def build_team(config: TeamConfig) -> Team:
    librarian_config = LibrarianConfig.load()
    tools = build_tools(librarian_config, build_embedder(librarian_config))
    doctor = DoctorAdapter(config.test_command, config.lint_command, config.timeout_seconds)
    mechanics = {
        "agent": AgentMechanic(
            lambda: gemini(config.model, config.api_key),
            config.test_command,
            config.lint_command,
            config.timeout_seconds,
        ),
        "human": HumanMechanic(),
    }
    return Team(config, doctor, LibrarianAdapter(tools), mechanics)


def print_evals(run: Run) -> int:
    results = evaluate(run)
    for r in results:
        print(f"  {'PASS' if r.passed else 'FAIL'}  {r.group:<10} {r.name}: {r.detail}")
    failed = [r for r in results if not r.passed]
    print(f"\n{len(results) - len(failed)}/{len(results)} evals passed.")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="codebase-team", description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="create a run; diagnose, brief, and stop at the approval gate")
    run.add_argument("--scenario", choices=sorted(SCENARIOS))
    run.add_argument(
        "--approve", action="append", metavar="PATH", help="approve PATH and continue (repeatable)"
    )
    run.add_argument("--rationale", default="")
    approve = commands.add_parser("approve", help="record the human approval for a run")
    approve.add_argument("task")
    approve.add_argument("--path", action="append", default=[], metavar="PATH")
    approve.add_argument("--rationale", required=True)
    approve.add_argument("--reject", action="store_true", help="record a refusal instead")
    for sub in (run, approve):
        sub.add_argument(
            "--allow-tests",
            action="store_true",
            help="let the Mechanic run the service tests - which runs the code it wrote",
        )
    cont = commands.add_parser("continue", help="patch (if approved) and verify")
    cont.add_argument("task")
    for sub in (run, cont):
        sub.add_argument("--mechanic", choices=("agent", "human"), default="agent")
        sub.add_argument(
            "--remember", action="store_true", help="let the Librarian remember a verified repair"
        )
    for name in ("evals", "inspect"):
        commands.add_parser(name).add_argument("task")
    commands.add_parser("list", help="list runs")
    args = parser.parse_args(argv)

    config = TeamConfig.load()
    if args.command == "list":
        for path in sorted(config.runs_dir.glob("task-*")):
            print(
                path.name, "-", (load_run(config.runs_dir, path.name).meta().get("scenario") or "no scenario")
            )
        return 0
    if args.command in ("evals", "inspect"):
        found = load_run(config.runs_dir, args.task)
        if args.command == "evals":
            return print_evals(found)
        print(report(found))
        return 0
    try:
        team = build_team(config)
    except ConfigError as exc:
        print(f"codebase-team: {exc}", file=sys.stderr)
        return 2

    commands_allowed = [TESTS_COMMAND] if getattr(args, "allow_tests", False) else []
    try:
        if args.command == "run":
            current, message = team.to_gate(args.scenario)
            print(f"{current.task_id}: {message}")
            if args.approve and message.startswith("Waiting"):
                team.approve(
                    current, args.approve, args.rationale or "Approved on the command line.", commands_allowed
                )
                print(team.past_gate(current, args.mechanic, args.remember))
            elif message.startswith("Waiting"):
                print(
                    f"Review {current.artifacts}, then:\n  codebase-team approve {current.task_id} "
                    "--path <file> --rationale <why> [--allow-tests]\n"
                    f"  codebase-team continue {current.task_id}"
                )
        elif args.command == "approve":
            current = load_run(config.runs_dir, args.task)
            record = team.approve(
                current, args.path, args.rationale, commands_allowed, approved=not args.reject
            )
            decision = "refused" if args.reject else f"approved {', '.join(record.allowed_paths)}"
            print(f"{current.task_id}: {decision}")
        else:
            current = load_run(config.runs_dir, args.task)
            print(team.past_gate(current, args.mechanic, args.remember))
    except (ValueError, FileNotFoundError) as exc:
        print(f"codebase-team: {exc}", file=sys.stderr)
        return 2
    print(f"\nArtifacts: {current.artifacts}\nTrajectory: {current.trajectory_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
