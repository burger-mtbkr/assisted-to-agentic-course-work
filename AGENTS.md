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

Student-added (created as you work through the module's exercise):

- `prompts/` - numbered spec -> prompt -> plan artifacts, e.g.
  `1-web-api-specs.md`, `2-web-api-prompt.md`, `3-web-api-plan.md`
- `JOURNAL.md` - that module's collaboration journal
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
- Persona subagents matching the course's Role + Action + Context model:
  `planner`, `architect`, `coder`, `reviewer`, `ui-designer`. Use them the
  way the course teaches roles - hand planning/design work to `planner` or
  `architect` before letting `coder` implement, then use `reviewer` to check
  the result.
