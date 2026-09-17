# Workflow and Status

Episodic memory: how work gets done here, and a pointer to what's currently
in flight. Detailed tracking lives in the active work item file under
`changes/`; this document defines the process and holds only a lightweight
pointer to current status.

## Four-stage process

Every work item moves through four stages, in order, one at a time:

1. **PLAN** - break the work into Given-When-Then tasks; for the current
   task, define test strategy and file changes before touching code.
2. **BUILD & ASSESS** - implement, then validate: tests pass, and `npm run
   check` (test + lint + format:check + type-check, see
   `context/ENV_SCRIPTS.md`) is clean.
3. **REFLECT & ADAPT** - what friction came up, does the remaining task list
   need adjusting, does this document or `ENV_SCRIPTS.md` need a fix.
4. **COMMIT & PICK NEXT** - commit, review touched READMEs, purge the work
   item's stage-tracking notes, pick the next task.

### Stage 1: PLAN

- Break the story into Given-When-Then acceptance criteria (if not already
  done for the work item).
- For the current task: define test strategy (what needs coverage - unit,
  integration, edge cases) and file changes (which files, what kind of
  change).
- **Output**: a filled-in "STAGE 1: PLAN" section in the work item file,
  committed.
- **Done when**: the user confirms the test strategy and file list are
  clear enough to build from.

### Stage 2: BUILD & ASSESS

- Implement the task: tests first where practical, then the code that makes
  them pass.
- Run `npm run check` from `config-service/`. Every part of it - tests,
  lint, format, type-check - must be clean. No skipped tests, no suppressed
  warnings.
- Verify behavior matches the Given-When-Then, not just "tests are green."
- **Output**: working, tested code satisfying the task's acceptance
  criterion.
- **Done when**: the user confirms `npm run check` passes cleanly and the
  behavior matches the criterion.

### Stage 3: REFLECT & ADAPT

- What went well, what caused friction.
- Do the remaining tasks in the work item still make sense as scoped, or do
  they need to change?
- Does `ENV_SCRIPTS.md` or this document need a fix based on what just
  happened?
- **Output**: notes captured in the work item's "STAGE 3" section; any
  process-document edits made directly.
- **Done when**: the user confirms both the process review and the
  remaining-task review are done.

### Stage 4: COMMIT & PICK NEXT

- Commit with a clear, descriptive message in this repo's existing style:
  `"Module N: <what changed>"` (see `context/IMPLEMENTATION.md`'s
  Development workflow section - not conventional-commit prefixes). Commits
  go directly to `main`; this repo doesn't use feature branches for work
  items (auto-syncs to `origin/main` on commit).
- Check the README in every folder touched or created this task. Update any
  that no longer describe what's actually there.
- **Purge**: delete the STAGE 1-3 notes from the work item's "Current Task
  Focus" section. Keep only the acceptance criteria list (with the task
  marked complete) and, if useful, a one-line outcome note. The commit and
  the code are the record of what happened; the stage notes are working
  scaffolding, not history.
- Update "Current Status" below and the work item's "Current Task Focus"
  with the next task.
- **Output**: a clean commit, current READMEs, a pruned work item, a clear
  next task.
- **Done when**: the user directs starting the next task's PLAN stage.

## Stage transition rule

**Only the user decides when a stage is complete.** The assistant does not
declare a stage done or propose moving to the next one - it keeps working
the current stage until the user explicitly says to move on (e.g. "let's
move to BUILD & ASSESS"). This applies even when the work looks finished -
"looks done" and "user confirmed done" are different things.

## Work item structure

- One file per story: `changes/NNN-name.md` (three-digit, e.g.
  `001-feature-flags.md`).
- Copy `changes/template.md` to start a new one.
- A story contains multiple Given-When-Then tasks; each task is roughly
  1-3 commits and goes through all four stages on its own.
- Acceptance criteria format: Given-When-Then, one block per task, each with
  a `Status` (Not Started / In Progress / Complete).
- "Current Task Focus" in the work item tracks the single task in flight -
  its stage, and that stage's detail. Everything above the "purge" line in
  Stage 4 is temporary; everything below is permanent record.

> **Purge discipline**: plans and stage notes are scaffolding for doing the
> work, not the history of it. Once a task is committed, delete them from
> the work item. If you need to know what was done, read the code and the
> commit message - that's the truth. A work item file that only ever grows
> is a sign the purge step is being skipped.

## Current Status

- **Work item**: [changes/001-feature-flags.md](../changes/001-feature-flags.md)
- **Current task**: Task 4 - Client Consumption Pattern
- **Current stage**: PLAN - Not Started
- **Last updated**: 2026-09-17

*All detail lives in the work item file above. This section is a pointer,
nothing more - if it disagrees with the work item file, the work item file
wins.*
