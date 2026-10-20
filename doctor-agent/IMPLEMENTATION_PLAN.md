# Doctor Agent - Implementation Plan

Step 0 of `modules/assisted-to-agentic-module-7/project/STEPS.md`: the curriculum's
`PLAN.md` worksheet, filled in for this repo before any code.

## Decisions the worksheet asks for

| Question | Answer |
|---|---|
| Language | Python 3.13, managed with `uv` (same as `pair-agent/`) |
| Agent framework | LangChain Deep Agents (`deepagents` 0.7). Module 6 hand-rolled the loop; Module 7 is about what a framework takes over (loop, tool dispatch, filesystem tools, skill loading) and what is still ours to design (identity, scope, tools, process, evidence standard). |
| Model provider | Google Gemini, free Flash tier (`gemini-flash-latest`) through `langchain-google-genai` - the provider this repo already uses. The key lives in the git-ignored `doctor-agent/.env` and is read with `dotenv_values`, never put in `os.environ`, so the checks the Doctor runs cannot see it. |
| Interface | CLI REPL (`uv run --project doctor-agent doctor`) with streamed tool progress, plus `--ask` for a one-shot question (used for the recorded manual runs). |
| Target codebase | `../config-service` - this repo's own C#/.NET API and TypeScript admin UI, the same patient Modules 4-6 anchor to. Mounted as `/codebase/`. Configurable, so the curriculum's Python fixture can be diagnosed too. |
| Test command | `npm run test` (from `config-service/context/ENV_SCRIPTS.md`: `dotnet test` + `vitest`) |
| Lint command | `npm run lint` (`dotnet build` with warnings-as-errors + `dotnet format --verify-no-changes` + `eslint`) |
| Conversation artifacts | `.doctor-runs/conversations/conversation_<id>.jsonl` |
| Trace artifacts | `.doctor-runs/traces/trace_<id>.jsonl` |

## Boundaries, and where each is enforced

The Doctor must not edit code, and - a lesson from Module 6 - must not read
`config-service/.env`, which holds real AWS credentials. Prompt wording alone is
not a boundary, so each rule lives in code:

| Rule | Enforced by |
|---|---|
| Sees only what git tracks or would track (no `.env`, `node_modules`, `bin/obj`) | `GitScopedBackend` from the shared `../agent-kit/` package, mounted at `/codebase/` |
| Cannot write, edit or delete anything | `GitScopedBackend` with no writable paths, plus a Deep Agents `FilesystemPermission` denying every write |
| Small tool surface | A per-agent `ToolSurface` middleware (agent-kit) hides `write_file`, `edit_file`, `delete`, `execute`, `write_todos` and the `task` subagent, and refuses them if named. What is left: `ls`, `read_file`, `glob`, `grep`, `run_tests`, `run_lint`. (The first version used a Deep Agents harness profile; review showed that registry is process-wide and unions exclusions across agents, which would have stripped the Module 9 Mechanic's write tools.) |
| Checks run only the configured commands | `run_tests` / `run_lint` take no arguments; the model chooses *whether* to run a check, never *what* runs |

The mount, the Gemini wiring, the retry policy and the turn recording live in
`../agent-kit/` because Modules 8 and 9 need exactly the same plumbing (the
Mechanic adds write grants to the mount). One definition of "what an agent may
see" instead of three copies; each specialist keeps only what makes it that
specialist - prompt, tools, skills, mounts. (It started as a mount-only
package and was widened when the second agent needed the rest.)

## Step plan (STEPS.md 1-6)

1. **Conversation and identity** - `config.py`, `prompts.py`, `agent.py`, `cli.py`. Verify "What do you do?" against Gemini.
2. **Diagnostic tools** - `tools.py`: `run_tests` / `run_lint` return `tool, check, command, cwd, exit_code, passed, duration_ms, stdout, stderr` (+ `error`). Output over 6000 chars keeps head and tail around an explicit marker. On timeout the whole process tree is killed (on Windows, `npm` and `dotnet` outlive a killed `cmd.exe` and hold the pipes open). Unit tests use harmless `python -c` commands.
3. **Scoped filesystem** - `/codebase/` route on `GitScopedBackend`. Verify: list, read README, reject `.env` and a path outside the mount.
4. **Diagnostic skill** - `skills/triage-codebase-health/SKILL.md`, loaded by Deep Agents' skills middleware (catalog in the prompt, body read on demand). Skill use is recorded as a `skill_read` event.
5. **Observability** - `agent_kit.recording` / `agent_kit.harness`: one `RunRecorder` per session writing the conversation JSONL (user message, tool call, tool result, skill read, assistant message) and the trace JSONL (conversation turn, model call, tool call, final response - each with `duration_ms`). Fed from LangGraph's stream updates, so built-in tool calls are recorded as well as ours.
6. **End-to-end** - unit tests, ruff, and recorded manual runs against both `config-service` (healthy) and the curriculum's Python fixture (unhealthy: its planted `settings_test` failure), so both report paths and evidence-driven file inspection are seen.

## Tests

Deterministic, no model calls: the command tools (success, failure, timeout,
missing codebase, compaction), the recorder (schema and files), and the
assembled agent driven by a scripted fake chat model - which tools it was
offered, that `.env` and out-of-mount reads come back as errors, that writes
are refused, and that every event lands in the artifacts.
