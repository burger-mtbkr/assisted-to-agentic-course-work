# Module 9 Journal

## Entry 1: The Codebase Team - contracts, an approval gate, a live repair

- **Prompt**: "do 7 - 9 ..." then "continue" (next day)
- **Tool**: Claude Code (VS Code extension)
- **Mode**: Direct execution. Plan first
  (`codebase-team/IMPLEMENTATION_PLAN.md`, Milestone 0), then milestones 1-10.
  Deterministic tests before any live run.
- **Context**: `modules/assisted-to-agentic-module-9/project/` (DESIGN,
  EXERCISE, PLAN, STEPS, HANDOFF-TEMPLATES), `doctor-agent/`,
  `librarian-agent/`, `agent-kit/`, `config-service/`
- **Model**: Claude Opus 5.5 building. Gemini `gemini-3.5-flash` as the live
  Mechanic.
- **Input**: Adaptation level 2 for the Doctor and the Librarian (adapters over
  their Module 7 and 8 capabilities), and a live Deep Agents Mechanic behind the
  same port, with a human-assisted alternative. `config-service` is green, so a
  run can seed `duplicate-name-status` into its copy: `ErrorMiddleware` returns
  400 for a duplicate application name instead of 409.
- **Output**:
  - **`codebase-team/`:**
    - `AgentPort` and the five handoff artifacts, which validate themselves
      on write and read
    - per-run workspace: a copy of git-visible files with a git baseline,
      the source fingerprinted
    - a trajectory log, the orchestrator split at the human gate
    - 20 coordination evals (artifact, trajectory, permission, evidence,
      outcome), `inspect` and the CLI
  - **`agent-kit`:** `GrantedWriteBackend`, the Mechanic's mount, which writes
    only approved paths and is checked against resolved paths.
  - **23 tests, no provider.** The whole team runs on a miniature
    `config-service` whose `check.py` prints .NET-shaped output, with the
    real Deep Agents Mechanic driven by a scripted model. They cover:
    - the approved path
    - refusal without approval, and a refused approval
    - an out-of-bounds edit refused by the mount
    - a human's out-of-bounds edit reverted and flagged
    - a corrupted handoff and a patch before approval, both caught by evals
    - a healthy codebase stopping after diagnosis
  - **Two real bugs the tests found:**
    - The Doctor adapter crashed on output with no failures, so on every
      healthy codebase, including verification after a good repair. The live
      run had only ever hit the failing case.
    - `revert` treated a new file as tracked after `diff()` marked it
      intent-to-add, so an out-of-bounds new file survived. It now compares
      against the baseline commit.
  - **Live run `task-20261021-191836-ef1d`:**
    1. The Doctor named the failing test (Expected 409, Actual 400) and quoted
       the test and the `catch` block.
    2. The Librarian's brief brought the 409 decision note and the
       knowledge-graph warning. It bounded the edit to `ErrorMiddleware.cs`
       and marked the test as the contract.
    3. `continue` before approval was refused, and nothing changed.
    4. The human approved the middleware only.
    5. Gemini read the skill, the code and the test, ran the tests (red),
       made one edit, and ran them again (green).
    6. The Doctor verified, and the Librarian remembered the repair. A later
       Librarian query returns that note first.
    7. 20/20 evals passed, and the source fingerprint was unchanged.
- **Cost**: Free tier; the Mechanic used 6 model calls.
- **Reflections**: The ambiguity was the point of the scenario. A failing test
  says "code and test disagree", not which is wrong. A Mechanic alone could
  "fix" it by editing the test. The structure prevented that three times: the
  Librarian's brief named the contract, the approval excluded the test, and
  the mount would have refused the edit anyway.

## Review fixes and the second live run

- **Prompt**: "Review codebase-team for correctness and safety" (reviewer
  subagent), then fix every finding.
- **Tool**: Claude Code
- **Mode**: Agent
- **Context**: `codebase-team/`, `agent-kit/` mount, the Librarian adapter.
- **Model**: Opus 5.5 (review and fixes); Gemini `gemini-3.5-flash` (Mechanic).
- **Input**: The reviewer's findings on the gate, the evals and verification.
- **Output**:
  - The gate checks the task id, refuses a "proposal" approval, and needs a
    valid diagnosis and brief. Approvals need the brief first, and grants are
    recorded as the workspace spells them.
  - Tests are opt-in (`--allow-tests`), because running them runs the
    Mechanic's code.
  - A crashed specialist is a failed step: its edits are reverted and the run
    still ends. The original is re-fingerprinted after every step.
  - Verification fails if tests vanish or more are skipped. The diff and
    status use a scratch git index and see deletions and ignored files.
  - Drill repairs are remembered as "uncertain"; the old drill note was marked
    uncertain.
  - Evals grew to 23 (run at rest, edits came from the patch step, no test
    lost).
  - **Live run `task-20261021-194732-77d4`:** the first Mechanic attempt hit
    the free-tier daily limit; the edit-free failure was recorded and the run
    ended cleanly. `continue` on `gemini-3.5-flash` repaired, verified (87 of
    87 tests), and passed 23/23 evals.
- **Cost**: Free tier; one Mechanic turn.
- **Reflections**: The quota failure was an unplanned test of the crash path,
  and it behaved: the run said why it stopped, and continuing on another model
  picked up from the gate without redoing the diagnosis.

## Agent Hub: one browser UI over every agent

- **Prompt**: "run module 6 so I can use it", then "I want a react UI with MUI
  controls ... history, new session buttons etc like Claude has", then "one
  UI for the different agents ... pick between the doctor, the librarian, the
  pair agent", "best in class ... light and dark mode".
- **Tool**: Claude Code (VS Code extension)
- **Mode**: Agent. Reviewer subagent on the first (PAIR-only) web UI; its
  findings were designed into the hub rather than patched.
- **Context**: `pair-agent/`, `agent-kit/`, `doctor-agent/`,
  `librarian-agent/`, `codebase-team/`
- **Model**: Claude Opus 5.5 building. Gemini free tier live:
  `gemini-flash-lite-latest` (PAIR, Mechanic), `gemini-3.1-flash-lite`
  (Doctor, Librarian).
- **Input**: Four agents in four uv projects, three of them chat agents with
  different loops (a hand-rolled one and Deep Agents), and one workflow with a
  human gate.
- **Output**:
  - `agent-hub/` at the repo root: one uv environment importing the agents as
    path dependencies, a Starlette API, and a React 19 + MUI 9 UI (Inter, light,
    dark and system themes, Ctrl+K and Ctrl+Shift+O).
  - Chats with PAIR, Doctor and Librarian: streamed tokens, live tool calls with
    readable results, loaded skills named as skills, working memory, the
    agent's tools, skills and prompt, export and import (PAIR exports `/save`
    format), per-agent free-model picker kept across restarts.
  - Codebase Team runs in the browser: start (with a seeded regression), a
    step tracker, the approval form, diagnosis, brief, patch, diff,
    verification and the 23 evals.
  - Stop waits for a running tool and ends before the next model call, then
    rolls the turn back; a stopped first turn discards the empty chat and
    returns the text to the composer. A turn outlives a reload.
  - Upstream: agent-kit events carry the tool call id; `Team.gate(run)` split
    from `to_gate`; `open_runtime` takes provider settings as a mapping so the
    hub never loads a `.env` into the environment the Doctor's test
    subprocesses inherit.
  - Live: PAIR, Librarian (two turns, resumed from saved state) and Doctor
    (real tests and lint) answered through the hub; a Stop during the
    Doctor's test run waited ~2 minutes for it, then rolled back. A full Team
    run `task-20261022-005543-80a3` driven through the UI was approved in the
    browser, verified, and passed 23/23 evals, changing only
    `ErrorMiddleware.cs`.
- **Cost**: Free tier. `gemini-flash-latest` and `gemini-3.5-flash` hit their
  daily quota during the session, which is why the model picker exists.
- **Reflections**: The first version put the UI inside `pair-agent/`; asking
  for every agent turned it into its own project, and the web code moved
  rather than being copied. The hard part was not the UI but Stop: cancelling
  an asyncio task does not stop a tool in a worker thread, so a "stopped" test
  run kept going under the next turn. Stopping at the next safe point instead
  of cancelling made both agent families behave the same way.
