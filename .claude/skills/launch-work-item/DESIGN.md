# Pairing Skill - Design Document: `launch-work-item`

**Module 4 exercise | Phase 2: Pair Agent | Option C (skill pair, 1 of 2)**

Filled-in copy of `modules/assisted-to-agentic-module-4/examples/SKILL_DESIGN_TEMPLATE.md`. The grounding script
is designed in
[SCRIPT-DESIGN.md](SCRIPT-DESIGN.md);
the paired closing skill in
[../land-work-item/DESIGN.md](../land-work-item/DESIGN.md).

---

## Skill overview

**Skill name** (used as the slash command):

```
/launch-work-item
```

**One-line description:**

Orients you on a single task inside a `changes/NNN-*.md` work item before
the PLAN stage starts - reads the workflow pointer, the work item's
Given-When-Then, and what the repo has actually been doing, then produces a
launch brief with the task in scope, the files it will touch, and one
specific first action.

**When would you invoke this?**

At the moment of picking up a task - either the first task of a new work
item, or the next task after the previous one landed. The friction it
answers is concrete and was felt repeatedly across Modules 1-3: the
four-stage workflow in `config-service/context/WORKFLOW_STATUS.md` says the
PLAN stage starts from "the current work item and stage," but finding those
means opening `WORKFLOW_STATUS.md`, following its pointer to the work item
file, scrolling past completed tasks to find the active one, then
separately checking git to see what actually happened since. Four manual
reads, in a fixed order, every single time. That is a process, and a
process with a fixed recipe is a skill.

It is deliberately *not* a general "where were we?" orientation skill (the
demo's `start-work` already is one). It only answers: **which task am I
about to plan, and what do I need to know to plan it well?**

---

## Inputs

**Explicit inputs:**

| Input | Description | Required? |
| --- | --- | --- |
| Work item / task hint | e.g. "002", "task 3", or "the caching work item" | No - defaults to whatever `WORKFLOW_STATUS.md`'s Current Status points at |
| Project directory | Which project inside the repo to orient on | No - auto-discovered by locating `context/WORKFLOW_STATUS.md` |

**Implicit inputs:**

| Input | Where it comes from | Why it's needed |
| --- | --- | --- |
| Current Status pointer | Script: the `## Current Status` section of `context/WORKFLOW_STATUS.md` | The single source of truth for which work item and stage are live |
| Work item body | Script: the resolved `changes/NNN-*.md` | Supplies the Given-When-Then the plan has to satisfy, plus the Notes that constrain it |
| Per-task status roll-up | Script: counts the `**Status**:` lines in the work item | Shows what is already done, so the brief does not re-plan finished work |
| Work item commit history | Script: `git log --follow -- <work item file>` | Shows how the story has actually progressed, commit by commit |
| Recent repo commits and touched files | Script: `git log --oneline -10`, `git diff --name-only` | Shows the code trajectory the new task lands on top of |
| Per-file history for touched files | Script: `git log --oneline -5 -- <file>` | Shows whether a file in scope is churning or stable |
| Working tree state | Script: `git status --porcelain` | A dirty tree at launch means the previous task did not land cleanly - a blocker, not a detail |
| Open TODO/FIXME/HACK | Script: grep in recently touched files | Unfinished work left by the last session, in the files the new task will touch |
| Context doc freshness | Script: last commit date per `context/*.md` | Lets the brief flag a context doc that has not moved while the code it describes has |
| Documented commands | Script: the `npm run` lines from `context/ENV_SCRIPTS.md` | So the brief names *this* repo's gate (`npm run check`), never an improvised `dotnet test` |

---

## What the LLM does

**Step 1 - Resolve what is actually in scope.**
Run the script. Read `=== WORKFLOW POINTER ===` and `=== WORK ITEM ===`
first. Identify the single task in flight: the first task whose status is
`In Progress`, else the first `Not Started`. If the user gave a hint that
disagrees with the pointer, say so explicitly rather than silently picking
one - a stale pointer is itself a finding worth surfacing.

**Step 2 - Form the file hypothesis, then reconcile it against evidence.**
From the task's Given-When-Then and the work item's Notes, predict which
files change, which get read, and which are new. Then read
`=== RECENT COMMITS ===`, `=== FILES TOUCHED ===` and
`=== PER-FILE HISTORY ===` and correct the prediction. Where the work item
names an existing pattern to mirror (this repo's convention - e.g. the
`Configurations` vertical slice), name the specific sibling files to copy
from rather than describing the pattern abstractly.

**Step 3 - Assemble the brief and stop at the gate.**
Write the sections below, then stop. This skill does not start the PLAN
stage, does not edit the work item file, and does not declare a stage
complete - `context/WORKFLOW_STATUS.md` reserves all of that for the user.
Close by asking for confirmation of the scope list.

---

## Output format

**Format:** Markdown, fixed sections, no preamble.

**Sections the output should always include:**

1. **In scope** - work item ID and title, the active task number, its
   Given-When-Then quoted verbatim from the file (not paraphrased), and the
   stage the pointer says we are in.
2. **Where the work stands** - tasks complete vs remaining, the commits
   that carried this work item so far, and the state of the working tree.
3. **Scope** - files likely to be modified, files to read first, new files
   to create, and the sibling files to mirror for each new one.
4. **Watch out for** - dirty tree, open TODOs in files in scope, context
   docs that look stale, and anything the script could not determine
   (explicitly, never silently).
5. **First action** - one specific next step, and the PLAN-stage output it
   should produce (test strategy + file changes, per `changes/template.md`).

**What should NOT be in the output:**

- Generic engineering advice not grounded in the script's evidence.
- Paraphrased acceptance criteria - the Given-When-Then is quoted, because
  the plan gets judged against its exact words.
- A test-suite verdict, unless `--with-check` actually ran. Absence of
  evidence is reported as absence of evidence.
- Any statement that a stage is complete or that it is time to move on.

---

## Script responsibility

| Fact | How the script gets it | Format passed to LLM |
| --- | --- | --- |
| Project root | Walk up from CWD for `context/WORKFLOW_STATUS.md`, else search the repo | One path line |
| Current Status pointer | `sed` the `## Current Status` section | Raw markdown block |
| Active work item path | Parse the pointer's `changes/NNN-*.md` link; fall back to highest-numbered file | One path line |
| Work item body | `cat` the resolved file | Raw markdown |
| Task status roll-up | `grep -c` on the `**Status**:` variants | `Complete: N, In Progress: N, Not Started: N` |
| Work item commit history | `git log --oneline --follow -- <file>` | Hash + subject list |
| Recent commits | `git log --oneline -10` | Hash + subject list |
| Files touched | `git diff --name-only HEAD~10..HEAD` | Flat path list |
| Per-file history | `git log --oneline -5 -- <file>` | Per-file blocks |
| Working tree state | `git status --porcelain` | Raw porcelain, or `(clean)` |
| Open TODOs | `grep -nE 'TODO|FIXME|HACK'` on touched files | Per-file line lists |
| Context doc freshness | `git log -1 --format=%ad` per `context/*.md` | `file - date` table |
| Documented gate command | `grep` the `npm run` lines out of `context/ENV_SCRIPTS.md` | Command list |
| Optional gate result | `npm run check` behind `--with-check` | PASS/FAIL + failing tail |

> Every row needs the current state of *this* repo. None of it is guessable
> from training data, which is exactly the line the module draws for when a
> script earns its place.

---

## Failure modes to consider

**If invoked by a human:** the brief is advisory. A wrong file list gets
spotted while planning and corrected in conversation. Cost is a minute.

**If invoked by the pair agent in Module 6:** the brief becomes the agent's
working scope. A missed file means the plan omits a change; a stale pointer
means planning the *wrong task*; a silently-skipped gate means building on
a red tree and blaming the new code. Errors compound downstream, so the
skill fails loudly rather than guessing.

**Validation the skill includes:**

- Every section with no evidence prints an explicit `(none found)` or
  `(could not determine)`, and the skill body tells the LLM to surface
  those rather than omit the section.
- Pointer/work-item disagreement is reported, never silently resolved.
- The gate is not run by default, and the brief must say it was not run
  rather than implying green.
- The brief ends with "I've identified these N files as in scope - correct
  me before we plan," keeping a human in the loop at the point where being
  wrong is cheapest.

---

## How you'll know it's working

**Test invocation:**

```
/launch-work-item
```

(with `config-service/context/WORKFLOW_STATUS.md` pointing at
`changes/001-feature-flags.md`, story complete, no active task)

**Expected output (rough sketch):**

```
## In scope
Work item 001 (Feature Flags) - all 5 tasks Complete. The pointer says
"Current task: None - next work item not yet created (changes/002-<name>.md)".
There is no active task to launch, so there is nothing to plan yet.

## Where the work stands
5/5 tasks Complete. The work item was carried by ~12 commits ending at
<hash> "Module 3: ...". Working tree clean.

## Watch out for
- No changes/002-*.md exists; the next launch needs one created from
  changes/template.md first.
- Quality gate not run (invoke with --with-check to include it).

## First action
Create changes/002-<name>.md from changes/template.md, fill in Story
Details and the Given-When-Then task list, then re-invoke this skill.
```

The "no active task" case is the sharper test than the happy path: a skill
that only worked with a task in flight would return a confidently wrong
brief on the very state this repo is in right now.

---

## Notes and decisions

- **Why not extend `start-work`?** `start-work` answers "where were we?"
  across a whole repo. This answers "which task am I planning, and against
  which acceptance criteria?" Different question, different evidence, and
  merging them would have produced exactly the Swiss-army-knife the module
  warns about.
- **The gate is opt-in on launch, mandatory on landing.** `npm run check`
  takes minutes and needs a stopped API process; paying that on every
  orientation would make the skill something you avoid invoking. Landing is
  the moment the gate genuinely has to run, so `land-work-item` runs it
  unconditionally.
- **Project auto-discovery instead of a hard-coded `config-service/`.** The
  script keys off `context/WORKFLOW_STATUS.md` existing, so the skill still
  works if the repo grows a second project using the same framework. Same
  reason the gate command is read out of `ENV_SCRIPTS.md` rather than
  hard-coded.
- **Quoting the Given-When-Then verbatim was a deliberate constraint.**
  Module 3's reflections recorded acceptance criteria drifting when
  paraphrased between stages. Quoting removes the opportunity.
