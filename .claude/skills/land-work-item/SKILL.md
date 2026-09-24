---
name: land-work-item
description: Run the closing process on a work item task you think is finished - runs the quality gate for real, checks the change against its Given-When-Then, lists the READMEs and context docs that drifted, works out which stage notes to purge, and drafts the commit message. Use this whenever a task looks done, before committing, when wrapping up or closing out a piece of work, or when asked to check whether something is ready to commit in a project following the context/ + changes/ workflow framework. Reports and hands over; never commits on its own.
---

# Land Work Item

You run the closing process on a task the user believes is finished. That
belief is the trigger, and it is also the risk: the interesting part is
over, which is exactly when the closing steps get skipped.

`context/WORKFLOW_STATUS.md` asks for five things at the end of a task - a
clean quality gate, behaviour verified against the acceptance criteria, a
README review of every touched folder, the stage-note purge, and a commit
in this repo's message style. You produce all five as evidence, and then
you hand over. You do not commit, and you do not declare the stage done.

## Inputs

- **Task hint** (optional): which task is being landed, if the work item's
  pointer is ambiguous.
- **`--skip-check`** (optional): skip the quality gate, e.g. it was run
  minutes ago in this same session. Report the skip as loudly as a failure.
- **Project directory** (optional): auto-discovered like `launch-work-item`.

## How to do this

### Step 1 - Establish the gate result before anything else

Run the script first, before any reasoning:

```bash
bash .claude/skills/land-work-item/script.sh
```

It runs the project's `check` script for real and can take several minutes.
Pass `--skip-check` only if the user asks for it.

Read `=== BLOCKING PROCESSES ===` and then `=== QUALITY GATE ===` before
anything else.

- **Blocking process found**: a running `ConfigApi.Service` locks the build
  output and makes the gate fail with `MSB3027` for reasons that have
  nothing to do with the code. Report that as the cause, tell the user to
  stop the process and re-run, and do not read the failure as a code
  defect.
- **Gate FAIL**: the report is short. Give the failure with its real
  output, and stop. Nothing else in the closing process matters while the
  gate is red, and a tidy commit message under a failing build is actively
  misleading.
- **Gate SKIPPED**: say so in the Gate section in plain terms - the landing
  is unverified.

### Step 2 - Judge the change against the acceptance criteria, clause by clause

Take the active task's Given / When / Then. For **each clause**, point at
the specific evidence in `=== DIFF STAT ===` and `=== WORKING TREE ===`
that satisfies it - a file, a test name, an endpoint - and give a verdict:
met, partially met, or **no evidence**. The absence has to be visible.

`context/IMPLEMENTATION.md` is explicit that green tests are not the same
as behaviour verified. Where a clause needs a live check against the
running API or the Admin UI, say that rather than quietly counting the
mocked unit suite as proof.

### Step 3 - Produce the closing checklist

Work through `=== README REVIEW ===`, `=== DOC DRIFT ===`,
`=== STAGE SECTIONS ===` and `=== COMMIT STYLE ===`:

- **READMEs**: for each touched folder, does it have a README, did it
  change, and does it still describe what is actually there now.
- **Doc drift**: context docs that did not move while the code they
  describe did; and `openapi.json`, which `context/ENV_SCRIPTS.md` records
  as going "stale silently - nothing checks it" after a controller or model
  change.
- **Purge**: name the exact `### STAGE N` headings to delete from the work
  item and what remains - the acceptance criteria with the task marked
  complete, plus at most a one-line outcome note.
- **Commit message**: match the subjects in `=== COMMIT STYLE ===`. This
  repo uses plain descriptive messages (`Module N: <what changed>`), never
  conventional-commit prefixes.

### Step 4 - Hand over, do not act

Do not commit. Do not edit the work item. Do not mark the task Complete and
do not say the stage is done - `WORKFLOW_STATUS.md`'s stage transition rule
reserves that for the user. End by listing the edits you are ready to make
on their word.

## Output

Markdown, these sections, in this order:

1. **Gate** - PASS / FAIL / SKIPPED per sub-gate (test, lint, format:check,
   type-check), with the real output on failure and the elapsed time.
2. **Acceptance** - the task's Given / When / Then, each clause paired with
   its evidence and an explicit verdict.
3. **READMEs to review** - every touched folder: has a README, changed,
   needs attention.
4. **Docs that drifted** - context docs and `openapi.json`, with the reason
   each is suspected stale.
5. **Purge plan** - the exact sections to delete, and what remains.
6. **Draft commit message** - subject plus body, in this repo's style.
7. **Ready when you are** - the edits you will make once the user confirms.

A section with nothing in it says `(nothing)` in one line. Never claim the
gate passed without `=== QUALITY GATE ===` backing it.
