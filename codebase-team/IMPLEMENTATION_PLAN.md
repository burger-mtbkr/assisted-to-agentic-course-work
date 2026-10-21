# Codebase Team - Implementation Plan

Milestone 0 of `modules/assisted-to-agentic-module-9/project/PLAN.md`: the
exercise translated into this repo's workflow before any code.

## Starting assets (adaptation level per specialist)

| Specialist | Prior asset | Level | How |
|---|---|---|---|
| Doctor | `doctor-agent/` (Module 7) | 2 - adapter over existing capabilities | `doctor_agent.tools.run_check` (process-tree timeouts, compaction) runs the checks in the run workspace; the adapter parses the .NET test output into a `DiagnosisReport` / `VerificationReport` and reads only the files the failures name |
| Librarian | `librarian-agent/` (Module 8) | 2 - adapter over existing capabilities | `LibrarianTools` over the Module 8 memory: hybrid `retrieve_context`, notes, knowledge-graph warnings, `file_history`; assembled into a `ContextBrief`. Writes only to its own memory (retrieval artifacts, and a repair note after a verified repair) |
| Mechanic | new | 1 - a live agent | Deep Agents + Gemini through `agent-kit`, with the workspace mounted writable **only** at the approved paths. A second, human-assisted Mechanic sits behind the same port |

Why the Doctor and Librarian are adapters rather than live agents here: their
team jobs - run the checks, retrieve the context - are deterministic sensors
already; a model adds cost and variance without adding judgement. The patch is
the one step that needs a model. Both live agents still exist on their own
(`doctor`, `librarian`).

## Target and scenario

`config-service` (C#) is green, so a team run needs a failure to repair. A run
can be created with `--scenario duplicate-name-status`: the workspace copy (never
the original) gets a known regression - `ErrorMiddleware` maps
`DuplicateApplicationNameException` to 400 instead of 409. It is the
counterpart of the curriculum fixture's planted settings failure: one guarding
test fails (`ErrorMiddlewareTests.DuplicateApplicationNameException_MapsTo409`),
and the repair is ambiguous on its own - change the code back to 409, or change
the test to expect 400? The Librarian's memory (the 409 decision note, the
`openapi.json` contract, the knowledge-graph warning) is what settles it, and the
approval boundary (middleware only, tests read-only) is what enforces it.

Checks in the run workspace are the API's own: `npm run test:api` and
`npm run lint:api`. The workspace is a copy of git-visible files only (no
`node_modules`), so the UI suite is out of scope for team runs.

## Layout

```text
codebase-team/
  src/codebase_team/
    artifacts.py    # AgentRequest/AgentResult + the five handoff artifacts, with validation
    port.py         # AgentPort protocol
    workspace.py    # per-run workspace: copy, git baseline, scenario, fingerprints, diff
    scenarios.py    # seeded regressions for drills
    trajectory.py   # JSONL event log
    doctor.py       # Doctor adapter: diagnose / verify
    librarian.py    # Librarian adapter: retrieve_context / remember_repair
    mechanic.py     # Mechanic port + agent (Deep Agents) and human implementations
    orchestrator.py # the pipeline and the approval gate
    evals.py        # artifact, trajectory, permission, evidence and outcome evals
    inspection.py   # replay a run from its artifacts
    cli.py          # create-run / run / approve / continue / evals / inspect / list
  skills/repair-issue/SKILL.md
  tests/
.codebase-team-runs/<task-id>/   (git-ignored)
  run.json  workspace/  artifacts/{diagnosis,context_brief,approval,patch_summary,verification}.json
  trajectory.jsonl  mechanic/{conversations,traces}/
```

## Boundaries and where each is enforced

| Rule | Enforced by |
|---|---|
| The original `config-service` is never modified | runs work on a copy; a fingerprint of the source's visible files is taken at creation and checked by the permission eval |
| Doctor and Librarian do not modify the workspace | workspace fingerprint before and after each step, recorded in the trajectory and evaluated |
| No patch without approval | the Mechanic port refuses unless `approval.json` exists, validates and says `approved: true`; the refusal is a `patch_blocked` event |
| The Mechanic edits only approved paths | `agent-kit`'s write grant (a mount that writes only granted paths, after resolving them inside the root) + a Deep Agents write permission per path + the post-patch diff check; out-of-bounds changes are reverted and the patch marked failed |
| Success is claimed only on verified evidence | the workflow result comes from `VerificationReport.status`, and the outcome eval checks it |

## Milestones (PLAN.md 1-10)

1. Shell and run workspace - `create-run` twice: separate dirs; source untouched.
2. Contracts - artifacts with required-field validation and round trips.
3. Doctor diagnosis - red run on the scenario; no workspace change.
4. Librarian context - brief cites docs, source, tests, memory, Git; gaps.
5. Approval gate - default not approved; `continue` without approval is blocked and logged.
6. Mechanic - agent and human adapters; approved paths only.
7. Doctor verification - green after a good patch; explicit remaining failures otherwise.
8. Trajectory and inspect - a run is explainable from its artifacts.
9. Evals - all pass on a good run; negative cases (no approval, corrupted artifact, out-of-bounds edit, wrong order) fail for the right reason.
10. Repair memory - after verification only; cites all four artifacts.
