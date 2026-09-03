---
description: Scaffold the student-work folders inside a newly-added course module and surface that module's instructions.
---

Scaffold module $ARGUMENTS of the "Assisted to Agentic" course:

1. Confirm `assisted-to-agentic-module-$ARGUMENTS/` exists at the repo root. If it doesn't, stop and tell the user to add that curriculum folder first.
2. Inside it, create `prompts/` if it doesn't already exist.
3. Inside it, create `JOURNAL.md` if it doesn't already exist, with a top-level `# Module $ARGUMENTS Journal` heading.
4. Read `assisted-to-agentic-module-$ARGUMENTS/README.md` and, if present, `assisted-to-agentic-module-$ARGUMENTS/project/INSTRUCTIONS.md`, and summarize for the user what this module covers, what the exercise asks them to do, and what (if anything) it says about extending a previous module's project folder in place.

Only create files directly under `assisted-to-agentic-module-$ARGUMENTS/prompts/`, `assisted-to-agentic-module-$ARGUMENTS/JOURNAL.md`, and (later, per the exercise) that module's own project folder. Don't modify the curriculum-provided files (`README.md`, `project/INSTRUCTIONS.md`, `project/INTEGRATE.md`, `examples/`, `slides.pdf`).
