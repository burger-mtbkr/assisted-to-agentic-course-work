# Pairing Skill - Script Design Document: `land-work-item/script.sh`

**Module 4 exercise | Phase 2: Pair Agent | Option C (skill pair, 2 of 2)**

Filled-in copy of `examples/SCRIPT_DESIGN_TEMPLATE.md`, for the skill
designed in
[land-work-item-SKILL-DESIGN.md](land-work-item-SKILL-DESIGN.md).

---

## Script overview

**Script name:**

```
.claude/skills/land-work-item/script.sh
```

**One-line description:**

Runs the project's quality gate for real and collects everything the
closing process needs to judge - the uncommitted diff, the folders and
READMEs it touches, the docs that did not move with it, the stage notes
still sitting in the work item, and a sample of the repo's commit style.

**When does the skill invoke this script?**

First, before any reasoning, exactly like the launch script - but the
ordering inside the script matters more here. The blocking-process check
runs before the gate, and the gate runs before everything else, because a
red gate short-circuits the entire report.

---

## Inputs

| Input | Source | Description |
| --- | --- | --- |
| `--project-dir <path>` | command-line arg | Explicit project root; skips auto-discovery |
| `--work-item <path\|NNN>` | command-line arg | Explicit work item; overrides the pointer |
| `--skip-check` | command-line flag | Do not run the gate (e.g. it ran minutes ago). Reported loudly in the output |
| Working directory | environment | Starting point for auto-discovery |
| Git repository | environment | Source of the diff, the folder roll-up, and the commit style sample |

---

## Operations

**Operation 1 - Locate project, pointer, and work item.**

- What it does: the same resolution the launch script performs.
- Approach: identical logic, deliberately duplicated rather than shared.
  See Notes.
- Produces: `=== PROJECT ===`, `=== WORKFLOW POINTER ===`,
  `=== WORK ITEM ===`, `=== TASK STATUS ===`.

**Operation 2 - Check for a blocking build process.**

- What it does: detects a running API that would lock the build output.
- Approach: `tasklist` on Windows, `pgrep`/`ps` elsewhere, matching
  `ConfigApi.Service`. Print the documented stop command when found.
- Produces: `=== BLOCKING PROCESSES ===`, before the gate section, so the
  cause is visible above the symptom.

**Operation 3 - Run the quality gate.**

- What it does: runs the project's documented `check` script for real.
- Approach: read the script name from `package.json` (`check`), run it with
  output captured to a temp file, record the exit code. On failure, print
  the last 40 lines. With `--skip-check`, print an explicit SKIPPED notice
  instead of running anything.
- Produces: `=== QUALITY GATE ===` with `PASS`, `FAIL`, or `SKIPPED`, the
  command run, and the elapsed seconds.

**Operation 4 - Capture the uncommitted change.**

- What it does: shows what is actually being landed.
- Approach: `git status --porcelain`, `git diff --stat`,
  `git diff --cached --stat`.
- Produces: `=== WORKING TREE ===`, `=== DIFF STAT ===`. Prints `(clean)`
  when there is nothing, so the "nothing to land" case is unambiguous.

**Operation 5 - Roll up touched folders and their READMEs.**

- What it does: turns "review the READMEs you touched" into a list.
- Approach: `dirname` each changed path, unique-sort, then for each folder
  report whether `README.md` exists and whether it is itself in the changed
  set.
- Produces: `=== README REVIEW ===` as
  `<folder> - README: yes/no, changed: yes/no`.

**Operation 6 - Detect doc drift.**

- What it does: flags documentation that should probably have moved.
- Approach: split the changed paths into source paths and `context/*.md`
  paths; list both. Separately, if any `Controllers/` or `Models/` path
  changed while `openapi.json` did not, emit a flag line.
- Produces: `=== DOC DRIFT ===`.

**Operation 7 - List stage sections still in the work item.**

- What it does: drives the purge plan.
- Approach: `grep -n '^### STAGE'` on the work item file.
- Produces: `=== STAGE SECTIONS ===` with heading plus line number, or
  `(none - already purged)`.

**Operation 8 - Sample the commit style.**

- What it does: gives the LLM the repo's real message conventions.
- Approach: `git log -8 --format=%s`.
- Produces: `=== COMMIT STYLE ===`.

---

## Output format

**Output format:** sectioned plain text on stdout, same
`=== SECTION NAME ===` convention as the launch script, in the order the
skill body reads them (blocking processes and gate first).

**Example output sketch:**

```
=== PROJECT ===
/c/dev/assisted-to-agentic-course-work/config-service
(found by walking up from the working directory)

=== BLOCKING PROCESSES ===
(none)

=== QUALITY GATE ===
command: npm run check
result: PASS (134s)

=== WORKING TREE ===
(clean)

=== DIFF STAT ===
(no uncommitted changes)

=== README REVIEW ===
(no changed files to review)

=== DOC DRIFT ===
(no changed files)

=== STAGE SECTIONS ===
(none - already purged)

=== COMMIT STYLE ===
Module 3: journal entry for the cross-module compliance audit
Fix silently-broken coverage filters, close the gaps they were hiding
...
```

---

## Error handling

| Scenario | What the script should do |
| --- | --- |
| Not inside a git repo | `=== ERROR ===` with a clear message, exit 0 |
| No `context/WORKFLOW_STATUS.md` found | `=== ERROR ===` naming where it looked, exit 0 |
| No `package.json` / no `check` script | `=== QUALITY GATE ===` reports `(no 'check' script - see context/ENV_SCRIPTS.md)`; the rest of the report still runs |
| `npm` not installed | Same treatment - report it, continue |
| Gate fails | `FAIL` + last 40 lines, exit 0. A red gate is the report's most important finding, not a script error |
| Gate takes very long | Report elapsed seconds so a slow gate is visible rather than mysterious |
| API process running | Warn in `=== BLOCKING PROCESSES ===` and still run the gate - the warning explains the likely `MSB3027` |
| Clean tree | Every change-derived section prints an explicit empty marker |
| Work item already purged | `(none - already purged)`, not an empty section |

> Same rule as the launch script: exit 0 on every expected condition. The
> script's product is evidence, including evidence of problems, and a
> non-zero exit would turn a finding into a tool failure.

---

## Dependencies and assumptions

| Dependency | Required? | What to do if missing |
| --- | --- | --- |
| `git` | Yes | `=== ERROR ===`, exit 0 |
| `bash` + POSIX toolchain | Yes | Assumed; Git Bash supplies them on Windows |
| `npm` | For the gate only | Report `(npm not found)` in that section, continue |
| .NET SDK / ESLint / Prettier | Transitively, via `npm run check` | Their absence shows up as a gate FAIL with real output |
| `tasklist` (Windows) or `ps`/`pgrep` | No | Report `(could not check)` in the blocking-process section |
| AWS credentials | No | `npm run check` runs the mocked unit suites only; nothing here touches DynamoDB |

**Which operating systems should this work on?**

- [x] macOS
- [x] Linux
- [x] Windows (Git Bash - the primary environment here; not WSL)

---

## Implementation prompt

```
Implement the bash script described in this design document as
.claude/skills/land-work-item/script.sh. Section names must match what
SKILL.md tells the LLM to read. Run the gate for real unless --skip-check
is passed, and put the blocking-process check before it. Exit 0 on every
expected condition. Then run it against config-service/ - including a real
--with-gate run - and show me the actual output.
```

---

## Testing checklist

- [x] Runs from the repo root and from inside `config-service/`
- [x] `--skip-check` skips the gate and says so unmistakably
- [x] A real run executes `npm run check` and reports PASS with an elapsed
      time
- [x] A deliberately broken source file produces `FAIL` with the real
      compiler output in the tail
- [x] Clean tree produces explicit empty markers, not silent empty sections
- [x] Dirty tree produces a correct folder/README roll-up
- [x] `openapi.json` drift flag fires when a controller changes without it
- [x] Stage-section detection finds `### STAGE` headings in an unpurged
      work item and reports `(none - already purged)` in `001`
- [x] Runs in a repo with no `check` script - reports it, keeps going

---

## Notes and decisions

- **The two scripts duplicate their resolution logic instead of sharing a
  helper.** A shared `lib.sh` would be better engineering in application
  code; here it would couple two skills that are meant to be
  independently installable and independently copyable into someone else's
  harness. The module's own guidance - self-contained skills, bundled
  resources under the skill directory - points the same way. The
  duplicated block is ~40 lines and is marked as such in both scripts.
- **40 lines of failure tail, not 20.** `dotnet build` with
  warnings-as-errors emits its summary well after the first diagnostic;
  20 lines regularly cut off the actual error. Found by breaking a file on
  purpose during testing.
- **Elapsed seconds on the gate** exist so a 3-minute gate reads as slow
  rather than hung, which matters when a Module 6 agent is deciding
  whether to wait.
