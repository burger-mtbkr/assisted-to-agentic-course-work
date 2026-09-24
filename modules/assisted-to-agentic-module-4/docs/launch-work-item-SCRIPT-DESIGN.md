# Pairing Skill - Script Design Document: `launch-work-item/script.sh`

**Module 4 exercise | Phase 2: Pair Agent | Option C (skill pair, 1 of 2)**

Filled-in copy of `examples/SCRIPT_DESIGN_TEMPLATE.md`, for the skill
designed in
[launch-work-item-SKILL-DESIGN.md](launch-work-item-SKILL-DESIGN.md).

---

## Script overview

**Script name:**

```
.claude/skills/launch-work-item/script.sh
```

**One-line description:**

Gathers the deterministic facts a launch brief needs - the workflow
pointer, the resolved work item, the git trajectory behind it, and the
state of the tree - and prints them as sectioned plain text on stdout.

**When does the skill invoke this script?**

First, before any reasoning. Step 1 of the skill body is "run the script
and read `=== WORKFLOW POINTER ===` first." The LLM forms its file
hypothesis only after it has the evidence, so nothing in the brief predates
the script's output.

---

## Inputs

| Input | Source | Description |
| --- | --- | --- |
| `--project-dir <path>` | command-line arg | Explicit project root. Skips auto-discovery. |
| `--work-item <path\|NNN>` | command-line arg | Explicit work item file, or its three-digit number. Overrides the pointer. |
| `--with-check` | command-line flag | Also run the documented quality gate. Off by default (minutes, and needs the API process stopped). |
| Working directory | environment | Starting point for project auto-discovery. |
| Git repository | environment | All history facts come from `git` run inside it. |

---

## Operations

**Operation 1 - Locate the project root.**

- What it does: finds the directory holding the workflow framework.
- Approach: if `--project-dir` given, use it. Otherwise walk up from CWD
  looking for `context/WORKFLOW_STATUS.md`. If that fails, `find` the repo
  (max depth 3, excluding `modules/`, `node_modules/`, `bin/`, `obj/`) for
  the first match. Excluding `modules/` matters: the course's curriculum
  `examples/` folders contain their own `context/` trees, and matching one
  of those would orient the brief on read-only reference material.
- Produces: `=== PROJECT ===` with the resolved path and how it was found.

**Operation 2 - Read the workflow pointer.**

- What it does: extracts the `## Current Status` block from
  `context/WORKFLOW_STATUS.md`.
- Approach: `sed -n '/^## Current Status/,/^## /p'`, trimming a trailing
  heading if the section is not last in the file.
- Produces: `=== WORKFLOW POINTER ===` with the raw markdown block.

**Operation 3 - Resolve the active work item.**

- What it does: turns the pointer into a concrete file path.
- Approach: `--work-item` wins (a bare `NNN` is globbed to
  `changes/NNN-*.md`). Otherwise grep the pointer block for a
  `changes/NNN-*.md` reference. Otherwise fall back to the
  highest-numbered `changes/NNN-*.md` that is not `template.md`, and label
  the fallback in the output so the LLM knows the pointer failed.
- Produces: `=== WORK ITEM ===` with the path, the resolution method, and
  the full file contents.

**Operation 4 - Roll up task statuses.**

- What it does: counts how many tasks are Complete / In Progress / Not
  Started.
- Approach: `grep -c` per status on the `**Status**:` lines.
- Produces: `=== TASK STATUS ===` with the three counts plus each task
  heading paired with its status line, in file order, so the LLM can pick
  the active one without re-parsing the whole document.

**Operation 5 - Gather git trajectory.**

- What it does: shows how this work item and the surrounding code have been
  moving.
- Approach: `git log --oneline --follow -- <work item>`;
  `git log --oneline -10`; `git diff --name-only HEAD~10..HEAD` (falling
  back to `git log --name-only` when the repo has fewer than 10 commits);
  then `git log --oneline -5 -- <file>` for each touched file, capped at 25
  files so the output stays readable.
- Produces: `=== WORK ITEM HISTORY ===`, `=== RECENT COMMITS ===`,
  `=== FILES TOUCHED ===`, `=== PER-FILE HISTORY ===`.

**Operation 6 - Inspect the working tree.**

- What it does: reports uncommitted work.
- Approach: `git status --porcelain`; print `(clean)` when empty.
- Produces: `=== WORKING TREE ===`.

**Operation 7 - Grep open TODOs.**

- What it does: surfaces debt in the files the task will touch.
- Approach: `grep -nE 'TODO|FIXME|HACK'` over the touched-file list,
  skipping files that no longer exist and binary/build paths.
- Produces: `=== OPEN TODOS ===`, or `(none found)`.

**Operation 8 - Check context doc freshness.**

- What it does: shows when each context document last changed.
- Approach: `git log -1 --format=%ad --date=short -- <file>` per
  `context/*.md`.
- Produces: `=== CONTEXT DOCS ===` as `file - YYYY-MM-DD` lines.

**Operation 9 - Report the documented commands.**

- What it does: tells the LLM this project's real script names.
- Approach: `npm pkg get scripts` if `package.json` exists, else grep
  `npm run` lines out of `context/ENV_SCRIPTS.md`.
- Produces: `=== DOCUMENTED SCRIPTS ===`.

**Operation 10 - Optional quality gate.**

- What it does: runs the gate only when asked.
- Approach: with `--with-check`, run the project's `check` script and
  capture PASS/FAIL plus the last 20 lines on failure. Without it, print an
  explicit "not run" line naming the flag.
- Produces: `=== QUALITY GATE ===`.

---

## Output format

**Output format:** sectioned plain text on stdout, one
`=== SECTION NAME ===` header per fact group, matching the section names
the skill body tells the LLM to read. Plain text rather than JSON on
purpose: the payload is mostly markdown and git output, which JSON would
only escape, and the consumer is a language model, not a parser.

**Example output sketch:**

```
=== PROJECT ===
/c/dev/assisted-to-agentic-course-work/config-service
(found by walking up from the working directory)

=== WORKFLOW POINTER ===
## Current Status
- **Work item**: [changes/001-feature-flags.md](../changes/001-feature-flags.md) - Complete (all 5 tasks)
- **Current task**: None - next work item not yet created
...

=== WORK ITEM ===
path: changes/001-feature-flags.md (resolved from the pointer)
--- contents ---
# Work Item 001: Feature Flags
...

=== TASK STATUS ===
Complete: 5, In Progress: 0, Not Started: 0
  Task 1: Feature Flag Domain Model and API Contract -> Complete
  ...

=== WORKING TREE ===
(clean)

=== QUALITY GATE ===
(not run - pass --with-check to include it)
```

---

## Error handling

| Scenario | What the script should do |
| --- | --- |
| Not inside a git repo | Print `=== ERROR ===` with a clear message, exit 0 so the LLM sees the reason rather than an empty pipe |
| No `context/WORKFLOW_STATUS.md` found | Print `=== ERROR ===` naming the directories searched, exit 0 |
| Pointer has no work item reference | Fall back to the highest-numbered `changes/NNN-*.md` and label it `(fallback - pointer had no reference)` |
| No `changes/NNN-*.md` at all | Print `(no work items yet - copy changes/template.md to start one)` under `=== WORK ITEM ===` |
| Fewer than 10 commits | Use the whole history instead of `HEAD~10..HEAD` |
| No commits at all | Print `(no commit history)` per affected section |
| Touched file since deleted | Skip it in the TODO grep; do not error |
| `--with-check` but no `check` script | Print `(no 'check' script in package.json - see context/ENV_SCRIPTS.md)` |
| Quality gate fails | Report `FAIL` plus the last 20 lines; still exit 0, because a red gate is a *finding*, not a script error |

> Exiting 0 on every expected condition is deliberate. The script's job is
> to hand the LLM evidence, including evidence that something is wrong. A
> non-zero exit would surface in the harness as a tool failure and the
> finding would be lost.

---

## Dependencies and assumptions

| Dependency | Required? | What to do if missing |
| --- | --- | --- |
| `git` | Yes | Print `=== ERROR ===`, exit 0 |
| `bash` 4+ / POSIX toolchain (`sed`, `grep`, `find`) | Yes | Assumed present; Git Bash supplies them on Windows |
| `npm` | Only for `--with-check` and the script list | Report `(npm not found)` in that section only |
| Project following the `context/` + `changes/` framework | Yes | Reported as the `WORKFLOW_STATUS.md` not-found error |
| Network / AWS credentials | No | The launch path never touches DynamoDB |

**Which operating systems should this work on?**

- [x] macOS
- [x] Linux
- [x] Windows (Git Bash - the primary environment here; not WSL)

Windows is the actual development environment for this repo, so "works in
Git Bash" is the binding requirement, not an afterthought: no `realpath`
dependence, no `/tmp` assumptions beyond `mktemp`, and no GNU-only `sed`
flags.

---

## Implementation prompt

```
Implement the bash script described in this design document as
.claude/skills/launch-work-item/script.sh. Follow the section names
exactly - the skill body references them. Exit 0 on every expected
condition, including errors, and print an explicit marker for every
section that found nothing. Then run it against config-service/ in this
repo and show me the real output.
```

---

## Testing checklist

- [x] Runs from the repo root with no arguments (auto-discovers
      `config-service/`)
- [x] Runs from inside `config-service/` (walk-up discovery)
- [x] `--work-item 001` resolves the same file the pointer does
- [x] `--work-item 999` reports a clear not-found rather than an empty
      section
- [x] Runs in a repo with no `context/WORKFLOW_STATUS.md` - clean error,
      exit 0
- [x] Runs in a freshly-`git init`ed repo with zero commits
- [x] Output section names match the ones `SKILL.md` tells the LLM to read
- [x] Does not match the curriculum `examples/` trees under `modules/`
- [x] `--with-check` runs `npm run check` and reports PASS/FAIL

---

## Notes and decisions

- **The `modules/` exclusion in auto-discovery is not incidental.** The
  first draft's `find` matched
  `modules/assisted-to-agentic-module-4/examples/config-service/context/`
  before the real project. A skill that orients you on read-only
  curriculum material while telling you it found your project is worse
  than one that fails.
- **25-file cap on per-file history.** A refactor commit touching 200
  files would otherwise produce thousands of lines and push the useful
  sections out of the LLM's attention. The cap is stated in the output so
  truncation is visible.
- **No caching, no state, no writes.** The script is pure read plus
  optional test run, which makes it idempotent - one of the module's
  stated quality heuristics - and safe for the Module 6 agent to invoke
  unattended.
