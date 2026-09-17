---
description: Scaffold the student-work folders inside a newly-added course module and surface that module's instructions.
---

Scaffold module $ARGUMENTS of the "Assisted to Agentic" course:

1. Check for `assisted-to-agentic-module-$ARGUMENTS/` at the repo root (outside `modules/`) - the module's curriculum content is a zip downloaded from the course source and extracted by hand, and extracting it at the repo root (rather than straight into `modules/`) drops it in the old, pre-reorg location. If it's there:
   - If `modules/assisted-to-agentic-module-$ARGUMENTS/` doesn't exist yet, `git mv` the whole root folder there (preserves history).
   - If `modules/assisted-to-agentic-module-$ARGUMENTS/` already exists (this zip got extracted at the root again), don't overwrite student-added files (`prompts/`, `JOURNAL.md`, module-level `AGENTS.md`) - merge only the curriculum-provided files/folders (`README.md`, `.published-from-curriculum.json`, `project/`, `examples/`, `slides.pdf`) from the stray root copy into `modules/assisted-to-agentic-module-$ARGUMENTS/`, then remove the now-empty root folder. If anything in that merge is ambiguous (e.g. curriculum content that looks student-modified), stop and ask rather than guessing.
   - Either way, tell the user this happened and suggest extracting future module zips directly into `modules/` to skip this step.
2. Confirm `modules/assisted-to-agentic-module-$ARGUMENTS/` exists. If it doesn't (and step 1 found nothing to move), stop and tell the user to add that curriculum folder first.
3. Inside it, create `prompts/` if it doesn't already exist.
4. Inside it, create `JOURNAL.md` if it doesn't already exist, with a top-level `# Module $ARGUMENTS Journal` heading.
5. Read `modules/assisted-to-agentic-module-$ARGUMENTS/README.md` and, if present, `modules/assisted-to-agentic-module-$ARGUMENTS/project/INSTRUCTIONS.md`, and summarize for the user what this module covers, what the exercise asks them to do, and what (if anything) it says about extending a previous module's project folder in place.

Only create files directly under `modules/assisted-to-agentic-module-$ARGUMENTS/prompts/`, `modules/assisted-to-agentic-module-$ARGUMENTS/JOURNAL.md`, and (later, per the exercise) that module's own project implementation folder - which may live at the repo root (e.g. `config-service/`) rather than nested inside the module folder, if it's a shared project extended across modules. Don't modify the curriculum-provided files (`README.md`, `project/INSTRUCTIONS.md`, `project/INTEGRATE.md`, `examples/`, `slides.pdf`).
