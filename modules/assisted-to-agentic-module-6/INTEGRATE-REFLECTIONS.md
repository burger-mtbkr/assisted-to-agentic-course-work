# Module 6 - Integrate & Reflect

Module 6 ships no `project/INTEGRATE.md`, so this is organised around what
the module set out to teach (its README's learning objectives) and what
building and running the PAIR Agent actually showed about each.

## Summary

**What I did:** Built `pair-agent/`, a small harness around `config-service`
that assembles the Module 4 skills and the Module 5 MCP server. It has:

- a chat loop on Google Gemini Flash (free tier)
- a provider-neutral `messages` array
- a tool registry
- `list_skills` / `activate_skill` / `run_skill_script`
- read-only repo tools
- MCP tools discovered from `mcp.json`

Every flow in `STEPS.md` was validated against the real model.

**How it went:** The mechanics took an afternoon. Getting the agent to *use*
them in the right order took most of the effort, and the fix was where the
words sit, not more code.

**What I learned:** A harness is mostly plumbing, and the plumbing is the
easy part. What decides whether the agent behaves well is which
instructions it sees, where, and in what order. The repo's own `AGENTS.md`,
written for a human-supervised coding agent, fought the progressive
disclosure the harness was built to teach.

---

## 1. What an agent harness is - the minimal moving parts

Five things, and none is big: `agent.py` (the loop) is about 70 lines.
Conversation in, model call, "did it ask for tools?", run them, append, call
again, stop when it answers. Everything else is either a tool or a guard.

The guards were where the real decisions were:

- **A round limit with a forced answer.** Without a limit, a model that
  keeps looking things up never stops. With one, the harness tells it to
  answer with what it has and say what it could not check. That is a better
  outcome than a hard stop.
- **Whole-turn rollback.** If the provider fails after tools have already
  run, the array is left holding a tool call with no answer, and the next
  request can be rejected. Rolling back the whole turn, not just the last
  message, keeps the session usable. The first version got this wrong.

## 2. The messages array is the agent's working memory

Seeing it as data (`/messages`, `/save`) made three things concrete:

- **Memory is just re-sending.** "What was my previous question?" works
  because the whole array goes back on every call. Nothing is remembered
  anywhere else.
- **So cost grows with every round.** Each tool round re-sends every earlier
  tool result. The five-prompt validation session used 93k input tokens for
  1.7k tokens of output. This is the problem Module 7's compaction topics
  exist for.
- **A provider-neutral array is worth it.** It holds plain
  `system / user / assistant(tool_calls) / tool` dicts, and the provider's
  wire format is produced only at the boundary. Swapping providers touched
  `provider.py` and two lines of startup code; the loop, tools, skills, and
  MCP code did not change. The one provider quirk that leaks into the array
  is deliberate. Gemini attaches a "thought signature" to each tool call and
  rejects the next request unless it comes back with that call, so it is
  stored on the call.

## 3. Harness-owned tools vs MCP-discovered tools

From the model's side they look identical: a name, a description, a schema.
The difference is all on the harness side:

- **Harness-owned tools** (`read_file`, `search_code`, the skill tools) are
  functions in the same process. I control their descriptions, and they can
  depend on harness state: `activate_skill`'s schema lists the skill names
  as an enum.
- **MCP tools** arrive at startup from a separate process. Their
  descriptions are whatever the server author wrote. The server can also
  send instructions when it connects, which the harness puts into the system
  prompt instead of hard-coding "use domain-lang for domain terms".
  Prefixing them `mcp__<server>__<tool>` (Claude Code's convention) kept
  their origin visible in `/tools` and in every transcript.

Building the client side also explained Module 5's registration friction.
`mcp.json` has a `cwd`, the client passes only a whitelisted set of
environment variables to the server, and a server that will not start has
to be reported by name. These are harness decisions Claude Code had made
for me.

## 4. Progressive disclosure - and what competes with it

The mechanism is simple. At startup the harness reads only each
`SKILL.md`'s frontmatter (name and description) and returns the body only
on `activate_skill`. The catalog costs a few hundred tokens; each 5-6k skill
body is paid for only when used. A test checks the body is never in the
catalog.

What surprised me was how hard it was to get the model to *use* it. In
early runs, "I'm starting work on feature flags. Orient me first..." never
activated `launch-work-item`, even though that is exactly what the skill
is for. Two causes, both about attention rather than code:

1. **The repo's own `AGENTS.md` says to read the five `context/` files "at
   the start of each conversation".** The model obeyed that over the
   harness's "activate a matching skill". It is an eager-loading instruction
   written for a different harness, and it undoes progressive disclosure:
   28-35k characters loaded before the agent knew what the task was. The
   system prompt now says explicitly that a matching skill comes before
   those reads.
2. **Where the catalog sits matters.** As a list in the system prompt it was
   background. Put into the description of the tool the model is choosing
   between, with "call this FIRST", it worked. This is how Claude Code's own
   Skill tool presents its catalog. It is also Module 5's lesson for MCP
   descriptions again: if the agent does not pick it, fix the description.

With both fixes, Gemini Flash's first tool call on the orientation request
was `activate_skill`, before reading a single file. Activation is now also
enforced: `run_skill_script` refuses to run a skill that has not been
activated.

## 5. Loading MCP definitions from `mcp.json` and calling them

This worked first time against the Module 5 server, because that server had
already been tested through Inspector and an in-memory client. The
interesting moments were the server earning its keep in a new harness:

- An early run looked up `"Feature Flag"` (with a space) and got
  `not_found`; the graph only knew `FeatureFlag`, `feature_flag` and `flag`.
  It was a data gap found only because a model phrased things differently.
  Adding spaced aliases closed it.
- Every MCP answer cited real `src/ConfigApi.Service/...` paths, so the
  agent's follow-up reads went straight to the right files. That is the
  payoff of Module 5's decision to write repo-owned data instead of keeping
  the curriculum's Python paths.

## 6. Assembling the PAIR Agent around `config-service`

The combined run did what STEPS.md's step 6 describes:

1. Activated `launch-work-item`.
2. Ran its script, which reported "work item 001 complete, no task in
   flight".
3. Looked up FeatureFlag, FlagKey, FlagConsumptionPattern and ScanCache
   through the MCP.
4. Answered with the domain terms, their warnings (404 is not the same as
   false; boolean only), and the next step: create `changes/002-*.md`. It
   did not invent a plan for work that does not exist.

Things that only showed up by running the real stack on Windows:

- `subprocess.run(["bash", ...])` finds WSL's `System32\bash.exe` before Git
  Bash, so the harness resolves bash explicitly. The test for that caught a
  second bug in the resolver itself.
- Windows console and pipe encoding is cp1252. The harness crashed printing
  a model's arrow character (U+2192). That is the same failure class the
  Module 5 server already guarded against in the CLI it wraps, and I should
  have carried the lesson over without being bitten twice.
- The Module 4 `launch-work-item` frontmatter was not valid YAML (an
  unquoted `: ` inside the description). Claude Code is lenient, a strict
  parser is not, and the first startup crashed. I fixed the skill file and
  made the harness tolerant: a portable skill should parse everywhere, and a
  harness should not die on one malformed skill.

## 7. Manual verification over tests

The 57 tests prove the plumbing: message translation, rollback, the round
limit, skill parsing, path confinement, and MCP discovery against the real
server. Provider tests use a mocked HTTP transport, so no test calls the
model. None of them would have found the most important things learned
here: `AGENTS.md` overriding skills, the catalog's placement, and the
missing alias. Those came only from chatting with the agent and reading
`/messages` afterwards. The course's "watch it reach for its capabilities"
is the real acceptance test for a harness; unit tests are how you keep it
passing.

## 8. A harness's tools are its attack surface

The reviewer pass found two security holes I had not looked for, because
both are invisible from the happy path:

- `read_file` was confined to the repo root, but `config-service/.env` is
  inside the root and holds secrets.
- `run_skill_script` was "just running our own skill", but its arguments
  came from the model, and the skill's helper will `cat` any path given to
  it as a work item.

In a chat with a human, neither matters. In a harness, the model decides
the arguments, and any file or MCP result it reads can try to steer it. The
fixes are argument-level:

- refuse git-ignored files
- refuse `--project-dir`
- require every path to resolve inside the code directory
- run a script only for a skill that has been activated

"Read-only" turned out to be a property of what a tool accepts, not of its
name.

## 9. Who chooses the model provider

Not the assistant. The first build used a cloud provider I picked myself,
and it cost the user money they never agreed to spend. It was removed, and
the agent now runs on the provider and free tier the user chose. For a
harness the provider is a one-module decision technically, but it is the
owner's decision financially. `AGENTS.md` now says so.

## What I'd carry into Module 7

- Context cost is the first real problem: every tool result is re-sent on
  every round. Summarising old tool results, or dropping them once used, is
  the obvious next step.
- Instruction precedence needs a design, not prompt tweaks. Harness rules,
  repo `AGENTS.md`, and skill instructions all compete. Today it is "the
  system prompt says skills win", which worked, but only after the model got
  it wrong first.
- The provider seam held up under a real swap. An eval comparing models on
  the same orientation prompt is the natural Module 7 follow-up.
