# Assisted to Agentic - Course Workspace

This repo tracks a 9-week "Assisted to Agentic" course. Each week a new
`modules/assisted-to-agentic-module-N/` folder is added, and each module
folder is self-contained: it holds both the curriculum content and the
student's work for that week. Project implementation folders that get
extended across multiple modules (e.g. `config-service/`, started in
Module 1 and extended by Module 3) live at the repo root, as siblings to
`modules/`, rather than nested inside any one module's folder - they're
shared across modules, not owned by whichever module happened to start
them.

## Inside each `modules/assisted-to-agentic-module-N/`

Curriculum-provided (a zip downloaded from the course source and
extracted by hand - see its `.published-from-curriculum.json` - treat as
read-only reference material):

- `README.md` - module overview and learning objectives
- `project/INSTRUCTIONS.md` - that week's exercise steps
- `project/INTEGRATE.md` - reflection prompts
- `examples/` - reference material
- `slides.pdf`

**Known gotcha**: extracting that zip at the repo root (its default
behavior unless you extract straight into `modules/`) drops the module
folder in the old, pre-reorg location. If you ever see an
`assisted-to-agentic-module-N/` folder sitting at the repo root, that's
this, not a new convention - move it into `modules/` (see
`/new-module`'s step 1 for how to do this without clobbering student
work if `modules/assisted-to-agentic-module-N/` already exists) rather
than leaving it or treating it as correct. Simplest fix going forward:
extract new module zips directly into `modules/`.

Student-added (created as you work through the module's exercise), always
at the **module root**, never inside `project/` - the whole `project/`
folder is git-ignored as curriculum material, so anything put there is
silently untracked and lost on the next clone:

- `prompts/` - numbered spec -> prompt -> plan artifacts, e.g.
  `1-web-api-specs.md`, `2-web-api-prompt.md`, `3-web-api-plan.md`. Only
  when the module's exercise actually asks for prompts; don't force a
  module's artifacts into `prompts/` because earlier modules used it.
  Module 4 asks for *skill design docs*, and those live with the skill
  they describe (`.claude/skills/<name>/DESIGN.md` and `SCRIPT-DESIGN.md`)
  rather than in the module folder - same reasoning as `config-service/`
  living at the repo root: skills span modules (M4 builds them, M6 assembles
  them), so their docs belong at the level they span.
- `JOURNAL.md` - that module's collaboration journal
- `INTEGRATE-REFLECTIONS.md` - answers to `project/INTEGRATE.md`'s
  reflection questions, one heading per question
- a project implementation folder, if that module's exercise starts one
  and it's scoped to that module alone - shared/extended projects live at
  the repo root instead (see above)

## Journal entries

Every meaningful AI collaboration gets a journal entry before moving on:

- Prompt
- Tool
- Mode
- Context
- Model
- Input
- Output
- Cost
- Reflections

Use `/journal` to add one to the current module's `JOURNAL.md`.

## Workflow discipline

- Plan before Act: think through or get a plan, review it, then execute.
- Commit before iterating on or redoing a step, so experiments stay
  comparable.
- Capture durable, code-related preferences and conventions in this file as
  they come up - this is what "most AI coding tools load automatically"
  refers to in the course material.
- Don't add dependencies, scope, or files beyond what the current module's
  spec/prompt/plan calls for.
- When a later module extends an earlier module's project (e.g. Module 3
  adding feature flags to `config-service`, started in Module 1), check
  that module's INSTRUCTIONS.md for whether it extends the existing folder
  in place or starts a new one, and follow that rather than assuming.

## Tools set up for this course

- `/new-module <N>` - scaffold `prompts/` and `JOURNAL.md` inside
  `modules/assisted-to-agentic-module-N/` for a newly-added module, and
  summarize that week's instructions.
- `/journal` - append an entry to the current module's `JOURNAL.md` using
  the template above.
- Skills in `.claude/skills/`, built in Module 4, that bracket a unit of
  delivery in any project following the `context/` + `changes/` workflow
  framework (currently `config-service/`). Both are read-only reporters -
  they never edit the work item, never commit, and never declare a stage
  complete, because `context/WORKFLOW_STATUS.md` reserves that for the user.
  Each skill directory holds its `SKILL.md`, `script.sh`, and the design
  docs it was built from (`DESIGN.md`, `SCRIPT-DESIGN.md`); the shared
  resolution helpers live in `.claude/skills/_lib/workflow.sh` (not a
  skill - no `SKILL.md`), and both scripts need it present. Project-specific
  values are knobs at the top of `land-work-item/script.sh`, overridable via
  `LAND_*` environment variables:
  - `launch-work-item` - before the PLAN stage. Resolves the workflow
    pointer to a work item, picks the task in flight, quotes its
    Given-When-Then verbatim, and produces a launch brief (in scope, where
    the work stands, file scope, watch out for, first action). The quality
    gate is opt-in (`--with-check`).
  - `land-work-item` - when a task looks done. Runs `npm run check` for
    real, judges the change clause by clause against its Given-When-Then,
    rolls up touched folders against their READMEs, flags context-doc and
    `openapi.json` drift, names the `### STAGE` sections to purge, and
    drafts the commit message in this repo's style.
- `domain-lang` MCP server (`domain-lang-mcp/`, built in Module 5),
  registered at project scope in `.mcp.json`. Five read-only tools
  (`lookup_term`, `get_related_terms`, `list_domain_areas`,
  `validate_knowledge_graph`, `ping`) answering what a `config-service`
  domain term means here and which files implement it. It wraps the
  curriculum `knowledge-graph` CLI (git-ignored, Module 5 zip) over
  repo-owned data in `config-service/knowledge/`: when a change renames or
  moves something a node's `source_files` lists, update the YAML in the same
  commit and re-import (`config-service/knowledge/README.md`). A fresh clone
  must approve the project server once before Claude Code will start it.
- `pair-agent/` (built in Module 6) - this repo's own agent harness:
  `uv run --project pair-agent pair-agent`. Google Gemini (free-tier
  `gemini-flash-latest`; `GEMINI_API_KEY` in the git-ignored
  `pair-agent/.env`, never committed), the `.claude/skills/` skills with
  progressive disclosure, and the `domain-lang` MCP via `pair-agent/mcp.json`.
  Skill frontmatter must stay valid YAML (quote a `description` containing
  `: `): Claude Code and `pair-agent` both tolerate an unquoted colon, but a
  strict YAML parser in another harness rejects the whole skill.
- Phase 3 specialists (Modules 7-9), each a LangChain Deep Agents app at the
  repo root with its own `pyproject.toml`, git-ignored `.env` (the same
  free-tier `GEMINI_API_KEY`) and git-ignored run artifacts:
  - `agent-kit/` - the plumbing they share, so it exists once: the
    git-scoped read-only codebase mount (no `.env`, no build output, no
    links), Gemini wiring with retries, the per-agent `ToolSurface`, turn
    recording to JSONL, the console, and a `ScriptedModel` for tests. A
    specialist adds only its prompt, tools, skills and mounts. Do not use
    Deep Agents' `register_harness_profile` to trim tools: its registry is
    process-wide and unions exclusions across agents.
  - `doctor-agent/` (Module 7) - `uv run --project doctor-agent doctor`:
    diagnoses `config-service` with its own `npm run test` / `npm run lint`
    as no-argument tools and the `triage-codebase-health` skill; never edits.
  - `librarian-agent/` (Module 8) - `uv run --project librarian-agent
    librarian` (`seed`, `index`, `retrieve`, `inspect`, chat): durable
    decision notes, a rebuildable SQLite index with Gemini embeddings and a
    relationship graph seeded from `config-service/knowledge/`, Git as
    episodic memory, one hybrid `retrieve_context` call. Writes only to its
    git-ignored `.librarian-memory/`. Rules about memory (dated user sources,
    capped confidence, supersession, links only to indexed files) live in the
    store, not in prompts.
  - `codebase-team/` (Module 9) - `uv run codebase-team run|approve|continue|
    evals|inspect`: Doctor -> Librarian -> human approval -> Mechanic ->
    Doctor over a copy of `config-service`; the Mechanic writes only the
    approved paths and runs the tests only with `--allow-tests`; a crashed
    step is reverted and recorded; 23 coordination evals on a full run. `--scenario
    duplicate-name-status` seeds a regression into the copy, never the
    original.
  - Every specialist answers within a per-turn budget (`agent-kit`'s
    `RoundBudget`, 12 model calls). Gemini ignores `tool_choice="none"`, so
    a final round is enforced on the reply, not requested.
- `agent-hub/` - one browser UI over all of the above: `uv run --project
  agent-hub agent-hub` (http://127.0.0.1:8765), after `npm --prefix
  agent-hub/web install` and `npm --prefix agent-hub/web run build`. Chats
  with the PAIR Agent, the Doctor and the Librarian, saved in the git-ignored
  `agent-hub/.sessions/`; Codebase Team runs with the approval gate in the
  browser. React + MUI in `agent-hub/web/`. It imports the agents as
  libraries (one uv environment, path dependencies), so they are not
  duplicated: a change to an agent shows up in the hub. It never loads an
  agent's `.env` into `os.environ` (the Doctor keeps the key out of what its
  test subprocesses inherit); `pair_agent.runtime.open_runtime` takes the
  provider settings as a mapping for that reason.
- Gemini free tier is about 20 requests per model per day (reset midnight
  Pacific), and an agent turn costs one request per tool round. Probe with
  one-word prompts, and switch `GEMINI_MODEL` to another free model
  (`gemini-flash-lite-latest`, `gemini-3.5-flash`, `gemini-3.1-flash-lite`,
  `gemma-4-31b-it`) when one model's quota is spent (in `agent-hub`, use its
  model picker).
- Model providers: never call a paid AI or cloud API (or use credentials
  found on the machine) without the user's explicit approval for that
  provider. The PAIR Agent and the Phase 3 specialists use Gemini's free tier
  only.
- Persona subagents matching the course's Role + Action + Context model:
  `planner`, `architect`, `coder`, `reviewer`, `ui-designer`. Use them the
  way the course teaches roles - hand planning/design work to `planner` or
  `architect` before letting `coder` implement, then use `reviewer` to check
  the result.
