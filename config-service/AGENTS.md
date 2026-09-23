# Agent Instructions

This project has a context framework in `context/`. Read these files at the start of each conversation:

- `context/ABOUT.md` — project purpose, personas, and constraints
- `context/ARCHITECTURE.md` — patterns, data flow, and key decisions
- `context/IMPLEMENTATION.md` — languages, versions, dependencies, preferences
- `context/ENV_SCRIPTS.md` — environments, ports, env vars, and every
  developer script (install, run, test, lint, format, type-check)
- `context/WORKFLOW_STATUS.md` — the four-stage PLAN / BUILD & ASSESS /
  REFLECT & ADAPT / COMMIT & PICK NEXT process, and a pointer to the
  currently active work item under `changes/`

Load files selectively when they are relevant to the current task, with one
exception: before planning or implementing any change to this project, read
`context/WORKFLOW_STATUS.md` first. It defines the four-stage process this
project works in, and the rule that **only the user decides when a stage is
complete** - do not declare a stage done or move to the next one on your own
initiative. Ask what the current work item and stage are if it isn't obvious.

Before running any command, check `context/ENV_SCRIPTS.md` for the documented
one. Don't improvise a `dotnet`/`npm` invocation when a `npm run ...` script
already covers it.

When you discover something about the project that isn't captured here, update the relevant file.
