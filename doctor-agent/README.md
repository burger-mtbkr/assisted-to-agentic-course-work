# doctor-agent

The Module 7 Doctor: a diagnostic specialist for codebase health, built on
LangChain Deep Agents. It converses, runs the codebase's own test and lint
commands as tools, inspects files only where the evidence points, follows the
`triage-codebase-health` skill, and writes an evidence-based health report. It
does not edit code.

Plan and decisions: `IMPLEMENTATION_PLAN.md`. Assignment:
`modules/assisted-to-agentic-module-7/project/`.

## Run it

From the repo root:

```bash
uv run --project doctor-agent doctor                       # conversation
uv run --project doctor-agent doctor --ask "Is the codebase healthy?" --ask "What failed?"
```

Copy `.env.example` to `.env` (git-ignored) and set `GEMINI_API_KEY` - the
same free-tier Google AI Studio key `pair-agent` uses. In the REPL, `/artifacts`
prints where the session is recorded, `/reset` starts over, `/quit` exits.
Tool calls stream as they happen (`-> run_tests()`, `<- run_tests: ok
(passed=True, exit_code=0)`).

## Settings

| Variable | Default |
|---|---|
| `GEMINI_API_KEY` | required, kept in `.env` and read without entering `os.environ`; withheld from the checks' environment even when exported |
| `GEMINI_MODEL` | `gemini-flash-latest`. The free tier allows roughly 20 requests per model per day (reset at midnight Pacific); `gemini-flash-lite-latest`, `gemini-3.5-flash` and `gemma-4-31b-it` each have their own quota |
| `DOCTOR_CODEBASE_PATH` | `../config-service` |
| `DOCTOR_TEST_COMMAND` | `npm run test` |
| `DOCTOR_LINT_COMMAND` | `npm run lint` |
| `DOCTOR_COMMAND_TIMEOUT` | `300` seconds. On timeout the check and everything it started are stopped: on Windows it runs in a Job Object (`taskkill /T` misses orphaned grandchildren), elsewhere in its own process group |
| `DOCTOR_RUNS_DIR` | `.doctor-runs` |

To diagnose the curriculum's Python fixture instead (it has a planted failing
settings test):

```bash
DOCTOR_CODEBASE_PATH=../modules/assisted-to-agentic-module-7/examples/config-service \
DOCTOR_TEST_COMMAND="cd svc && uv run pytest -q" \
DOCTOR_LINT_COMMAND="cd svc && uv run ruff check ." \
uv run --project doctor-agent doctor
```

## Tools and boundaries

| Tool | Source | Notes |
|---|---|---|
| `run_tests`, `run_lint` | ours (`tools.py`) | no arguments - the model decides whether to run a check, never what runs. Returns `tool, check, command, cwd, exit_code, passed, duration_ms, stdout, stderr` (+ `error`); long output keeps its head and tail. The two take turns even when the model asks for both at once: `dotnet test` and `dotnet build` share `bin/` and `obj/` |
| `ls`, `read_file`, `glob`, `grep` | Deep Agents | over `/codebase/` (read-only) and `/skills/` |

`/codebase/` is the shared `agent-kit` mount: only files git tracks or would
track are visible, so `config-service/.env` (real AWS credentials),
`node_modules` and `bin/obj` never reach the model, and every write is refused.
`agent-kit`'s per-agent `ToolSurface` middleware removes `write_file`,
`edit_file`, `delete`, `execute`, `write_todos` and the `task` subagent from
what the model is offered, and refuses them if named anyway.
The checks themselves are not side-effect free: `dotnet test` and `pytest`
write build output and caches, all git-ignored.

## Artifacts

Each session writes, under `.doctor-runs/` (git-ignored):

- `conversations/conversation_<id>.jsonl` - `user_message`, `tool_call` (with
  arguments), `skill_read`, `tool_result` (status, `passed`, `exit_code`,
  compacted output), `assistant_message`, `error`
- `traces/trace_<id>.jsonl` - `model_call`, `skill_load`, `tool_call`,
  `final_response`, `conversation_turn`, each with `duration_ms` and a
  per-turn `trace_id`

## Tests

```bash
uv run --project doctor-agent pytest doctor-agent
uv run --project doctor-agent ruff check doctor-agent
```

No test calls a model: the assembled agent is driven by a scripted chat model
to check the offered tool surface, the read and write boundaries, follow-up
memory, error recovery, and every recorded event. The manual runs against
Gemini are in the Module 7 journal; excerpts are in `EXAMPLE_RUNS.md`.
