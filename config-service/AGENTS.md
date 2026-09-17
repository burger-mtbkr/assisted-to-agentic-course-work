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

Load files selectively when they are relevant to the current task.

When you discover something about the project that isn't captured here, update the relevant file.
