# Assisted to Agentic - Course Workspace

This repo tracks a 9-week "Assisted to Agentic" course. Each week a new
`assisted-to-agentic-module-N/` folder is added, and each module folder is
self-contained: it holds both the curriculum content and the student's work
for that week.

## Inside each `assisted-to-agentic-module-N/`

Curriculum-provided (synced from the course source - see its
`.published-from-curriculum.json` - treat as read-only reference material):

- `README.md` - module overview and learning objectives
- `project/INSTRUCTIONS.md` - that week's exercise steps
- `project/INTEGRATE.md` - reflection prompts
- `examples/` - reference material
- `slides.pdf`

Student-added (created as you work through the module's exercise):

- `prompts/` - numbered spec -> prompt -> plan artifacts, e.g.
  `1-web-api-specs.md`, `2-web-api-prompt.md`, `3-web-api-plan.md`
- `JOURNAL.md` - that module's collaboration journal
- the module's project implementation folder (e.g. `config-service/` in
  Module 1), which later modules may extend in place

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
  adding feature flags to Module 1's config service), check that module's
  INSTRUCTIONS.md for whether it extends the existing folder in place or
  starts a new one, and follow that rather than assuming.

## Tools set up for this course

- `/new-module <N>` - scaffold `prompts/` and `JOURNAL.md` inside
  `assisted-to-agentic-module-N/` for a newly-added module, and summarize
  that week's instructions.
- `/journal` - append an entry to the current module's `JOURNAL.md` using
  the template above.
- Persona subagents matching the course's Role + Action + Context model:
  `planner`, `architect`, `coder`, `reviewer`, `ui-designer`. Use them the
  way the course teaches roles - hand planning/design work to `planner` or
  `architect` before letting `coder` implement, then use `reviewer` to check
  the result.
