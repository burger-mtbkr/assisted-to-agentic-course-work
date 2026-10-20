# Module 7 Journal

## Entry 1: Build the Doctor on a framework, and keep its boundaries in code

- **Prompt**: "do 7 - 9. I need a summary of what we did for 7 - 9 in a readme
  file with notes ... i need to speak to it in a playback"
- **Tool**: Claude Code (VS Code extension)
- **Mode**: Direct execution, bypass permissions. Followed `STEPS.md` in order:
  the `PLAN.md` worksheet first (`doctor-agent/IMPLEMENTATION_PLAN.md`), then
  steps 1-6, each with tests and a manual run against the real model.
- **Context**: `modules/assisted-to-agentic-module-7/` (README,
  `project/EXERCISE.md`, `DESIGN.md`, `STEPS.md`, `PLAN_before.md` /
  `PLAN_after.md`, the reference `examples/doctor/`), `config-service/`
  (`context/ENV_SCRIPTS.md` for the real test and lint commands), and the
  Module 6 `pair-agent/` for this repo's Python conventions.
- **Model**: Claude Opus 5.5 building it. Inside the Doctor: Google Gemini
  free tier through `langchain-google-genai`. The manual runs used
  `gemini-flash-latest`, `gemini-flash-lite-latest`, `gemini-3.5-flash`,
  `gemini-3.1-flash-lite` and `gemma-4-31b-it` (see Entry 2 for why).
- **Input**: LangChain Deep Agents (`deepagents` 0.7.28) instead of Module 6's
  hand-rolled loop. Patient: this repo's own C#/.NET `config-service`, the
  same one Modules 4-6 anchor to, with its documented `npm run test` /
  `npm run lint`.
- **Output**:
  - `doctor-agent/`:
    - `run_tests` / `run_lint`: no-argument tools that return `tool, check,
      command, cwd, exit_code, passed, duration_ms, stdout, stderr`. Long
      output keeps its head and tail. On timeout the whole process tree is
      killed: on Windows, `npm` and `dotnet` outlive a killed `cmd.exe` and
      hold the pipes open.
    - The `triage-codebase-health` skill, loaded by Deep Agents on demand.
    - A Doctor identity prompt, and a CLI with `--ask` for scripted
      conversations.
  - `agent-kit/` (shared with Modules 8 and 9):
    - `GitScopedBackend`: the model sees only git-visible files, so
      `config-service/.env` with its real AWS keys is invisible, and writes
      are refused.
    - Gemini wiring, a retry policy, and harness-profile tool restriction.
    - `Session`: streams a turn and records it as conversation and trace
      JSONL.
  - 17 Doctor tests and 31 `agent-kit` tests. None calls a model: a scripted
    chat model drives the assembled agent.
  - Manual runs, all recorded under `doctor-agent/.doctor-runs/`:
    - **Identity and scope**: "What do you do?" gave the right identity and
      the no-edit boundary. `ls` and `read_file` on `/codebase/` worked.
      `.env` was refused ("git ignores it"). `/etc/hosts` was not found,
      because it is outside the mount. "Please fix any lint warnings" was
      declined, with a diagnosis offered instead.
    - **Ambiguity**: "Is it ready?" first ran a full triage. After a prompt
      change, it asked: ready to keep developing, merge, or deploy?
    - **Healthy diagnosis of `config-service`**: the Doctor read the skill,
      then ran `run_tests` and `run_lint` in parallel. Evidence: 87 .NET and
      5 UI tests passed, a clean build, `dotnet format` and ESLint clean.
      Files inspected: none, because there was no failure to trace.
    - **Unhealthy diagnosis of the curriculum's Python fixture**, through
      `DOCTOR_CODEBASE_PATH`: 1 failed and 54 passed. The Doctor read
      `settings_test.py` at the failing line, used `grep` to find `class
      Settings`, read `settings.py`, then listed `svc/` and found no `.env`.
      Its diagnosis was correct, and every file it opened traces back to
      test output. The follow-up "What failed, exactly?" was answered from
      evidence already gathered, with no new tool calls.
- **Cost**: No paid calls. Gemini free tier only. The run that hit the limit
  is Entry 2.
- **Reflections**: The framework removed the loop, tool dispatch,
  filesystem tools and skill loading - about 300 lines of Module 6 - and none
  of the design. The Doctor is still four decisions that are ours: identity,
  tools that take no arguments, a skill, and where the boundary lives. The
  most useful bug was silent. Deep Agents finds a model's tool-restriction
  profile by `<provider>:<model_name or model>`. I keyed it by a different
  attribute, so the profile matched nothing and the agent was quietly
  offered `write_file`, `edit_file`, `delete` and a sub-agent. The backend
  still refused writes, so nothing broke. A test that asserts the exact tool
  list caught it. A framework default you have not pinned with a test is a
  default you do not know you have.

## Entry 2: The free tier has a daily wall, and streamed calls are not retried

- **Prompt**: (same session) running the manual checks
- **Tool**: Claude Code
- **Mode**: Debug, then fix
- **Context**: the Gemini 429 and 503 payloads; Google's rate-limit page,
  which does not publish free-tier numbers
- **Model**: Claude Opus 5.5; Gemini free-tier models
- **Input**:
  - Halfway through the first manual session, every call failed with
    `429 RESOURCE_EXHAUSTED`. The payload named the bucket:
    `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, limit **20**, for
    `gemini-3.8-flash` (what `gemini-flash-latest` currently resolves to).
    My exploratory probes had spent it.
  - Separately, `gemma-4-31b-it` returned a 503 "high demand" mid-stream,
    and the run died. The model client's own retries do not cover streamed
    calls, and Deep Agents always streams.
  - In `--ask` mode the failure surfaced as a Python traceback.
- **Output**:
  - **Spreading quota**: the per-day quota is per model, so `GEMINI_MODEL`
    selects another free model per run. Listing models and making one cheap
    call each showed which are on this key's free tier
    (`gemini-flash-lite-latest`, `gemini-3.5-flash`, `gemini-3.1-flash-lite`,
    `gemma-4-31b-it`). Gemma 4 does tool calling on this API. `gemini-2.5-*`
    are retired for new users.
  - **Retry policy**: `agent-kit` wraps every model call in LangChain's
    `ModelRetryMiddleware`. It retries 5xx and per-minute 429s, but a spent
    per-day quota fails fast, because it resets at midnight Pacific and
    waiting is pointless.
  - **CLI**: `--ask` turn failures now print one line and exit 1.
- **Cost**: The 20 requests spent on probes were the cost.
- **Reflections**: On a free tier the budget is requests, not tokens, and a
  Deep Agents turn costs one request per tool round, so a full diagnosis is
  about 4-6 requests. Exploration should be cheap: probe with a one-word
  prompt, not an agent turn. And "the provider retries for you" is only true
  for the call shape you tested.

## Entry 3: Reviewer pass - links, orphans, a global registry, and one wrong finding

- **Prompt**: (same session) a `reviewer` subagent briefed to look for boundary
  holes, correctness bugs, spec gaps and dead code in `agent-kit/` and
  `doctor-agent/`, with no model calls allowed
- **Tool**: Claude Code, `reviewer` persona subagent (read-only), then the main
  session for fixes
- **Mode**: Review, then fix everything, then verify live again
- **Context**: both projects, the Module 7 spec, Deep Agents' installed source
- **Model**: Claude Opus 5.5 (main session and subagent); Gemini
  `gemini-3.1-flash-lite` for the re-verification run
- **Input**: The reviewer threw path tricks at the mount and nothing leaked:
  `.ENV`, trailing dots, `::$DATA`, `\?\` and `/codebase/C:/` paths. Its real
  findings:
  1. **Links**: a Windows junction, which needs no admin rights, made a
     git-ignored directory and an outside directory readable.
  2. **Timeouts**: `taskkill /T` misses grandchildren whose parent already
     exited, and those hold the pipes open. A 2s timeout took 20s, and with
     a long-lived orphan it would never return.
  3. **Overlapping checks**: `run_tests` and `run_lint` ran in parallel on
     the same .NET `bin/obj`.
  4. **Global tool registry**: Deep Agents' harness-profile registry is
     process-wide and unions exclusions, so a Module 9 Mechanic built after
     the Doctor would have silently lost its write tools.
  5. **Replayed history**: a middleware that patches a dangling tool call
     re-emits the history, and turn 2 re-recorded turn 1's tool calls.
  6. **Smaller issues**: a prompt that both sent "ready?" to triage and
     called it ambiguous; an unvalidated timeout setting; a config test
     that depended on the shell's environment; Ctrl+C killing the REPL;
     stale docs; no console tests.
- **Output**:
  - **Visibility**: a file is visible only by its own path, so links are
    never followed. A fixture root obeys its own `.gitignore` through a
    throwaway git dir.
  - **Process trees**: checks start suspended, join a Windows Job Object,
    then resume, so every descendant dies with the job. The test has an
    orphaned grandchild and finishes in seconds.
  - **Check lock**: a lock makes the two checks take turns.
  - **`ToolSurface`**: per-agent middleware replaces the harness profile,
    and a test proves two agents in one process keep separate tool sets.
  - **`Session`**: only the model and tools nodes count as new messages,
    and a test fails against the old logic.
  - **Environment**: the API key is withheld from the checks' environment
    even when exported.
  - **Smaller fixes**: the timeout setting is validated, the prompt is
    consistent, `Session` records interrupted turns, and the REPL survives
    them.
  - **Docs**: `EXAMPLE_RUNS.md` excerpts the recorded runs, and the
    `agent-kit` README covers `console.py`.
  - **Rejected finding**: one finding was wrong. The reviewer said `grep`'s
    line numbers should use `split("\n")` to agree with `read_file`. A probe
    through the real tools showed that `read_file` counts lines with
    `splitlines()`, so a form feed is a line break to both, and `offset`
    uses that count. The test now pins the actual contract: grep's line N
    is `read_file` offset N-1.
  - Tests: `agent-kit` 43, `doctor-agent` 23. A fresh live diagnosis of
    `config-service` gave Healthy, with the two checks run one after the
    other.
- **Cost**: Free tier; the re-verification was four model requests.
- **Reflections**: The junction finding is Module 6's lesson in a new costume.
  "Read-only, git-visible files" was a property of names, but the filesystem
  resolves names through links, so the rule has to be checked against where
  the bytes actually come from. The global registry is the framework version
  of the same trap: a setting that looks per-agent but is process-wide. And
  the grep finding is why a review gets verified rather than applied:
  "agree with read_file" was the right goal, and testing it through the real
  tool showed which split does that.
