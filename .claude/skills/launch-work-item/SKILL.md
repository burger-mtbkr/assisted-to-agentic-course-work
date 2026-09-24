---
name: launch-work-item
description: Orient on the task you are about to start in a changes/NNN-*.md work item, before the PLAN stage. Use this whenever you are picking up a work item task, starting or resuming a task, asking which task is next, or about to plan or scope a change in a project that follows the context/ + changes/ workflow framework - even if the user does not say "work item". Produces a launch brief: the active task and its Given-When-Then, what has been built so far, the files in scope, and one specific first action.
---

# Launch Work Item

You orient the user on **one task** inside a work item, immediately before
the PLAN stage of the four-stage workflow. This is not general repo
orientation - it answers a narrow question: *which task am I about to plan,
and what do I need to know to plan it well?*

Everything you assert comes from the script's evidence. If the script did
not find it, you do not claim it.

## Inputs

- **Work item / task hint** (optional): e.g. "002", "task 3", "the caching
  work item". Without one, the workflow pointer decides.
- **Project directory** (optional): auto-discovered by locating
  `context/WORKFLOW_STATUS.md`.

## How to do this

### Step 1 - Run the script and resolve what is actually in scope

Run `script.sh` from the skill directory, before any other reasoning:

```bash
bash .claude/skills/launch-work-item/script.sh
```

Pass `--work-item NNN` when the user named one, `--project-dir PATH` when
the project is ambiguous, and `--with-check` only when the user explicitly
wants the quality gate run (it takes minutes and needs the API process
stopped - see `=== DOCUMENTED SCRIPTS ===`).

Read `=== WORKFLOW POINTER ===` and `=== WORK ITEM ===` first. Then use
`=== TASK STATUS ===` to identify the **single** task in flight: the first
task marked `In Progress`, otherwise the first `Not Started`. If every task
is `Complete`, say so - there is nothing to launch, and the right answer is
that a new work item is needed.

If the user's hint disagrees with the pointer, report the disagreement
rather than silently picking one. A stale pointer is a finding.

### Step 2 - Form a file hypothesis, then correct it against the evidence

From the task's Given-When-Then and the work item's `### Notes`, predict
which files will be modified, which need reading first, and which are new.
Then read `=== RECENT COMMITS ===`, `=== FILES TOUCHED ===` and
`=== PER-FILE HISTORY ===` and correct that prediction against what the
repo has actually been doing.

Where the work item names an existing pattern to mirror - this project's
convention is vertical slices, e.g. `Controllers/Flags` mirroring
`Controllers/Configurations` - name the specific sibling files to copy
from. "Follow the existing pattern" is not useful; "mirror
`Services/Configurations/ConfigurationService.cs`" is.

### Step 3 - Write the brief, then stop

Produce the five sections below, in order, no preamble.

Then stop. Do not start the PLAN stage, do not edit the work item file, and
do not say a stage is complete. `context/WORKFLOW_STATUS.md` reserves stage
transitions for the user, and this skill exists to make that decision
well-informed rather than to pre-empt it.

## Output

Markdown, these sections, in this order:

1. **In scope** - work item ID and title, the active task number, its
   Given / When / Then **quoted verbatim** from the file, and the stage the
   pointer says we are in. Quote rather than paraphrase: the plan gets
   judged against the exact words, and paraphrase is where acceptance
   criteria drift.
2. **Where the work stands** - tasks complete vs remaining, the commits
   that carried this work item so far (`=== WORK ITEM HISTORY ===`), and
   the state of the working tree. A dirty tree at launch means the previous
   task did not land cleanly - lead with that.
3. **Scope** - files likely to be modified, files to read first, new files
   to create, each new one paired with the sibling file to mirror.
4. **Watch out for** - dirty tree, open TODOs in files in scope, context
   docs that look stale relative to the code, and anything the script could
   not determine. State the unknowns explicitly; an omitted section reads
   as "nothing to worry about", which is a different claim.
5. **First action** - one specific next step, and the PLAN-stage output it
   should produce (test strategy + file changes, per `changes/template.md`).

Close with: "I've identified these N files as in scope - correct me before
we plan." That keeps a human in the loop at the point where being wrong is
cheapest.

Do not include: generic engineering advice, paraphrased acceptance
criteria, a test-suite verdict when `--with-check` was not passed, or any
statement that a stage is done.
