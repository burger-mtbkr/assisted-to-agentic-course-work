# Module 7 - Integrate & Reflect

Module 7 ships no `project/INTEGRATE.md`, so this follows the module's eight
learning objectives (README) and what building and running the Doctor
actually showed about each.

## Summary

**What I did:** Built the Doctor (`doctor-agent/`) on LangChain Deep Agents. It
is a diagnostic specialist for this repo's own `config-service`, and it does
not edit code. It has:

- two no-argument check tools, the codebase's own `npm run test` / `npm run lint`
- read-only, git-scoped file access
- a `triage-codebase-health` skill
- conversation and trace JSONL for every session

Plumbing that Modules 8 and 9 reuse went into a shared `agent-kit/`: the mount,
Gemini wiring, retries, the per-agent tool surface, turn recording and the
console. I verified it live:

- a healthy diagnosis of `config-service`
- an unhealthy diagnosis of the curriculum's Python fixture, where every file
  opened traces back to test output
- the boundary refusals
- a clarifying question when the request was ambiguous

**How it went:** The framework made the agent quick to stand up. Most of the
effort went into things the framework does *not* decide:

- where boundaries are enforced
- how a check's whole process tree is stopped on Windows
- a free tier that allows 20 requests a day per model

A reviewer pass found two boundary holes worth the time: links, and a
process-wide tool registry.

**What I learned:** A framework moves the loop out of your code, not the
design. The Doctor is still identity, tool contracts, procedure and boundary.
The new failure mode is defaults you have not pinned down: the tool surface
the model is offered, a registry that is global, retries that do not cover
streaming.

---

## 1. Framework agent vs the Module 6 hand-rolled loop

Deep Agents took over everything Module 6's `pair-agent` hand-wrote: the
turn loop, tool dispatch, the filesystem tools (`ls`, `read_file`, `glob`,
`grep`), skill discovery with progressive disclosure, and streaming. That is
roughly 300 lines gone. What did not go away:

- **The tool surface is now a default to override, not a list to write.**
  Module 6 offered exactly the tools I registered. Deep Agents offers
  `write_file`, `edit_file`, `delete`, `execute` and a `task` sub-agent unless
  told otherwise, so read-only means *removing* things. The first attempt used
  the framework's harness profiles and silently matched nothing; the second
  worked but was process-wide (see 2). The test that pins the exact offered
  tool list is the most valuable test in the project.
- **The framework's helpers have shapes you must learn.** Deep Agents streams
  every model call, so the model client's own retries never fire; a
  `ModelRetryMiddleware` had to wrap the loop. Its stream re-emits history
  when a middleware patches a dangling tool call, so the turn recorder must
  count only model and tools nodes as new.

## 2. A focused identity with clear responsibility boundaries

The identity is one paragraph: diagnose, never repair, evidence before
claims, ask when ambiguous. The boundaries are in code, because a sentence
in a prompt is not a boundary:

| Boundary | Enforced by |
|---|---|
| no writes | the mount refuses every write; a deny-all write permission; write tools removed from the surface |
| no secrets | the mount shows only git-visible files, never through a link |
| no "what runs" choice | `run_tests` / `run_lint` take no arguments |
| no key leakage | the key is never in `os.environ`, and is stripped from the checks' environment anyway |

Running it showed the identity works: "Please fix any lint warnings" got a
polite refusal and an offer to diagnose. But the identity text had a
contradiction I wrote myself: it sent "is it ready?" both to triage and to a
clarifying question. The model followed whichever came first. A boundary
written twice in different words is two boundaries.

## 3. Building a conversational agent with an SDK

Conversation state is the message list the graph returns, carried into the
next turn whole, tool results included. That is why "What failed, exactly?"
was answered from the earlier test output with no new tool call. A failed
turn leaves the conversation as it was, so a 429 or a Ctrl+C does not
corrupt the session.

## 4. A small, deterministic tool set

Two custom tools, each returning `tool, check, command, cwd, exit_code,
passed, duration_ms, stdout, stderr`. Small surface, but the details took
real work:

- **Output compaction keeps head and tail.** Test runners print the failure
  summary last, so truncating the tail would hide exactly the evidence.
- **"Never raises" includes timeouts.** On Windows, `npm` and `dotnet`
  outlive a killed `cmd.exe`, and orphaned grandchildren survive
  `taskkill /T`. Only a Job Object - start suspended, assign, resume - stops
  everything a check started.
- **Two checks, one lock.** The model asked for tests and lint in the same
  step, Deep Agents ran them in parallel, and both write the same .NET
  `bin/obj`. The tools now take turns.

## 5. Tool calls as grounded sensors

The unhealthy run is the clearest example. The Doctor ran the checks, saw
`settings_test.py:161`, and read it. It used `grep` for `class Settings`,
read `settings.py`, then listed `svc/` to test its hypothesis that `.env` is
missing. Every file it opened was pointed to by the previous result. It
never browsed.

The healthy run is the other half: zero files inspected, "no failure to
trace". A sensor-driven agent does less work when things are fine.

## 6. A skill as reusable process

`triage-codebase-health` holds the procedure:

- checks first, both of them
- files only where the evidence points
- what makes a result healthy, unhealthy or inconclusive
- the report format

Deep Agents puts only the skill's name and description in the prompt and
reads the body on demand, and the recorder logs that read as `skill_read`.
In every health-check run the skill was read before any check ran. The
skill's description is a trigger. Mine listed "ready to work on", which
fought the clarifying-question rule until I removed it.

## 7. An evidence-based health report

Reports quoted real numbers: 87 + 5 tests, exit codes, durations, the failing
test and line. Two lapses, both instructive:

- **A follow-up named a file that does not exist** (`ui/src/App.tsx`). The
  model generalised from "a TypeScript UI". The fix was one prompt line:
  never name a file you have not seen in tool output.
- **The fixture report said "Uncertainties: None"** and recommended changing
  the test. The curriculum's intended repair is in `settings.py`. A
  diagnostic agent's "next step" is a suggestion, which is exactly why
  Module 9 puts a Librarian and a human approval between diagnosis and
  repair.

## 8. Inspecting conversation logs and traces

The conversation JSONL answers *what* happened: question, every tool call
with arguments, every result, the skill read, the reply. The trace answers
*how long*: in the fixture run on Gemma, model calls took 25-217 s while
the tools took milliseconds. The bottleneck is the model, not the checks.

The traces also caught the overlapping checks: two tool calls whose time
ranges overlapped in one step.

## What I'd carry into Module 8

- Shared plumbing, separate identities: the Librarian is `agent-kit` plus a
  prompt, tools, skills and a writable memory directory. The codebase stays
  read-only.
- Treat free-tier requests as the budget. Probe with one-word prompts; give
  every live run a purpose.
- Pin framework defaults with tests: offered tools, what counts as a new
  message, what is retried.
