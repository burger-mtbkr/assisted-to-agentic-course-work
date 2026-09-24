# Pairing Skill - Design Document: `land-work-item`

**Module 4 exercise | Phase 2: Pair Agent | Option C (skill pair, 2 of 2)**

Filled-in copy of `modules/assisted-to-agentic-module-4/examples/SKILL_DESIGN_TEMPLATE.md`. The opening half of
the pair is designed in
[../launch-work-item/DESIGN.md](../launch-work-item/DESIGN.md);
this skill's grounding script in
[SCRIPT-DESIGN.md](SCRIPT-DESIGN.md).

---

## Skill overview

**Skill name** (used as the slash command):

```
/land-work-item
```

**One-line description:**

Runs the closing process on a finished task - actually runs the quality
gate, checks the work against its Given-When-Then, lists the READMEs and
context docs that drifted, works out exactly which stage notes to purge,
and drafts the commit message - then hands all of it to you to decide on.

**When would you invoke this?**

When the code for a task is written and you think you are done. That is
precisely the moment the closing steps get skipped, because the
interesting part is over. `config-service/context/WORKFLOW_STATUS.md` asks
for five separate things at the end of a task - a clean `npm run check`,
behaviour verified against the acceptance criteria, a README review of
every touched folder, the stage-note purge, and a commit in a specific
message style - and Module 3's own reflections recorded the purge step
being the one that slips.

This is the bigger half of the pair and the one that rewards iteration:
each landing is a chance to notice a check worth adding for next time.

---

## Inputs

**Explicit inputs:**

| Input | Description | Required? |
| --- | --- | --- |
| Task hint | Which task is being landed, if the work item's pointer is ambiguous | No |
| `--skip-check` | Skip running the quality gate (e.g. it was just run in this session) | No - and the report says loudly when it was skipped |
| Project directory | Which project to land in | No - auto-discovered like the launch skill |

**Implicit inputs:**

| Input | Where it comes from | Why it's needed |
| --- | --- | --- |
| Active work item and task | Script: the `WORKFLOW_STATUS.md` pointer, then the work item file | Supplies the Given-When-Then the result is judged against |
| Quality gate result | Script: runs the project's `check` script for real | "Tests pass" is the one claim that must never be inferred |
| Blocking process check | Script: looks for a running `ConfigApi.Service` process | This repo's documented Windows gotcha - a locked `.exe` makes the gate fail with `MSB3027` for reasons unrelated to the code |
| Uncommitted diff | Script: `git status --porcelain` + `git diff --stat` (worktree and staged) | The actual change being landed |
| Folders touched | Script: directory roll-up of the changed paths | Drives the README review |
| README presence and staleness | Script: for each touched folder, is there a README, and was it changed? | Turns "review touched READMEs" from a memory exercise into a list |
| Context docs vs code touched | Script: which `context/*.md` changed against which source dirs changed | Surfaces documentation drift while it is still cheap to fix |
| API surface drift | Script: did controllers/models change without `openapi.json` changing? | `ENV_SCRIPTS.md` records that `openapi.json` "goes stale silently - nothing checks it" |
| Stage sections still present | Script: greps `### STAGE 1..4` headings in the work item | Drives the purge plan |
| Commit message style | Script: `git log -8 --format=%s` | So the draft matches the repo's real style rather than conventional-commit defaults |

---

## What the LLM does

**Step 1 - Establish the gate result before anything else.**
Run the script and read `=== QUALITY GATE ===` first. If it failed, the
landing report is short: report the failure with its output, and stop.
Nothing else in the closing process matters while the gate is red, and
producing a tidy commit message under a failing build is actively
misleading.

**Step 2 - Judge the change against the acceptance criteria, clause by
clause.**
Take the active task's Given / When / Then and, for each clause, point at
the specific evidence in the diff that satisfies it - a file, a test name,
an endpoint. Where a clause has no evidence, say so plainly. The rule from
`context/IMPLEMENTATION.md` applies: green tests are not the same as
behaviour verified, so call out anything that needs a live check against
the running API rather than quietly counting the unit suite as proof.

**Step 3 - Produce the closing checklist.**
Work through the README review, the doc-drift list, the purge plan, and
the commit message draft. For the purge, name the exact headings to delete
and what stays. For the commit message, match the style in
`=== COMMIT STYLE ===`.

**Step 4 - Hand over, do not act.**
Do not commit. Do not edit the work item. Do not mark the task Complete
and do not say the stage is done. `WORKFLOW_STATUS.md`'s stage transition
rule reserves that for the user, and this skill exists to make that
decision well-informed, not to pre-empt it. End by listing the edits you
are ready to make on their word.

---

## Output format

**Format:** Markdown, fixed sections, no preamble.

**Sections the output should always include:**

1. **Gate** - PASS/FAIL per sub-gate (test, lint, format, type-check) with
   the real output on failure, or a loud "SKIPPED" notice.
2. **Acceptance** - the task's Given/When/Then, each clause paired with the
   evidence for it, and an explicit verdict: met, partially met, or no
   evidence.
3. **READMEs to review** - every touched folder, whether it has a README,
   and whether that README moved in this change.
4. **Docs that drifted** - context docs and `openapi.json`, with the reason
   each is suspected stale.
5. **Purge plan** - the exact `### STAGE N` sections to delete from the
   work item, and what remains afterwards.
6. **Draft commit message** - in this repo's style, subject plus body.
7. **Ready when you are** - the list of edits the skill will make once the
   user confirms.

**What should NOT be in the output:**

- Any claim the gate passed that is not backed by `=== QUALITY GATE ===`.
- Committed changes, edited files, or a task marked Complete. This skill
  reports; the user decides.
- A conventional-commit prefix (`feat:`, `fix:`) - wrong style for this
  repo, per `context/IMPLEMENTATION.md`.
- Filler sections. A section with nothing in it says `(nothing)` in one
  line.

---

## Script responsibility

| Fact | How the script gets it | Format passed to LLM |
| --- | --- | --- |
| Project root, pointer, work item | Same resolution as `launch-work-item` | Path + raw markdown |
| Active task and its criteria | `**Status**:` roll-up + task headings | Task list with statuses |
| Blocking dotnet process | `tasklist`/`ps` for `ConfigApi.Service` | Warning line, before the gate runs |
| Quality gate | Run the project's `check` script, capture exit code and tail | PASS/FAIL + last 40 lines on failure |
| Uncommitted change | `git status --porcelain`, `git diff --stat`, `git diff --cached --stat` | Porcelain + stat blocks |
| The diff itself | `git diff` + `git diff --cached`, plus the head of each new file, capped at 400 lines | Unified diff, with a truncation marker when cut |
| Touched folders | `dirname` roll-up over changed paths | Unique folder list |
| README status per folder | `test -f <folder>/README.md` + membership in the changed set | `folder - README: yes/no, changed: yes/no` |
| Context doc drift | Changed `context/*.md` vs changed source dirs | Two lists, for the LLM to correlate |
| API surface drift | Changed `Controllers/`/`Models/` paths vs `openapi.json` | Flag line |
| Stage sections present | `grep -n '### STAGE'` in the work item | Heading + line number list |
| Commit style sample | `git log -8 --format=%s` | Subject list |

> The gate is the clearest case in this pair for a script. An LLM can read
> a test file and form an opinion; only running the suite establishes that
> it passes today, on this machine, with these changes.

---

## Failure modes to consider

**If invoked by a human:** worst case is a padded checklist - a README
flagged that did not need touching. Cheap, visible, ignorable.

**If invoked by the pair agent in Module 6:** much sharper. A falsely green
gate means the agent commits broken code and the next task builds on it. A
missed purge means the work item file grows until it stops being readable,
degrading every later launch brief. A commit message in the wrong style
pollutes the history the skill itself samples for style. So: the gate is
run for real and never inferred, `--skip-check` is reported as loudly as a
failure, and the skill stops at the handover instead of committing.

**Validation the skill includes:**

- Gate first, and a red gate short-circuits the whole report.
- The running-process check runs *before* the gate, so a `MSB3027` file
  lock is reported as "stop the API and re-run" rather than as a code
  failure.
- Each acceptance clause gets an explicit verdict, including "no evidence"
  - the absence has to be visible.
- No writes at all until the user confirms.

---

## How you'll know it's working

**Test invocation:**

```
/land-work-item
```

(run in `config-service/` with work item 001 complete and a clean tree)

**Expected output (rough sketch):**

```
## Gate
PASS - npm run check: test (API 152 passed, UI 18 passed), lint, format:check,
type-check all clean. Ran for real, 2m14s.

## Acceptance
Work item 001 is Complete on all 5 tasks and there is nothing uncommitted,
so there is no in-flight task to land. Nothing to judge.

## READMEs to review
(nothing - no uncommitted changes)

## Docs that drifted
(nothing)

## Purge plan
changes/001-feature-flags.md contains no STAGE 1-4 sections - already purged.

## Draft commit message
(nothing to commit)

## Ready when you are
Nothing to do. Start the next work item with changes/002-<name>.md.
```

The empty case is the real test again: a landing skill that invents work
on a clean tree would be worse than useless inside the Module 6 agent.

---

## Notes and decisions

- **Running the gate is the whole point.** An earlier sketch had the script
  only *report* the gate command and let the LLM ask the user to run it.
  That reproduces the exact friction the skill exists to remove, and it is
  the one fact a language model cannot get right by reasoning.
- **Stopping short of committing was a hard constraint, not caution.**
  `WORKFLOW_STATUS.md` states only the user decides when a stage is
  complete, and Module 3's reflections honestly recorded that rule being
  bypassed under time pressure. Building the gate into the skill is how the
  rule survives contact with a Module 6 agent that would otherwise happily
  commit.
- **The project-specific knowledge is real, and it is kept in one place.**
  The `ConfigApi.Service` process check earns its place: `ENV_SCRIPTS.md`
  documents it as a Windows gotcha that has actually bitten, and its
  failure mode (`MSB3027`) looks like a build error, which is the worst
  kind of misleading evidence to hand a report that leads with the gate.
  But it is not the only project-specific fact - the API-surface paths,
  the spec file, the regen command and the source-dir pattern are too. All
  of them sit as named knobs at the top of `script.sh`, each overridable
  by a `LAND_*` environment variable, so the description's claim that the
  skill works for any project on the framework is actually true.
- **The acceptance verdicts rest on the diff, not the stat.** The first
  version pointed the LLM at `=== DIFF STAT ===` for evidence. A stat line
  cannot tell you whether "the cached entry is invalidated on delete" holds.
  The script now includes the bounded diff, and the skill body says to read
  any file the truncation cut before giving a verdict on it.
- **Next iteration, if this gets used enough:** have the purge plan emit
  the resulting file rather than describing it, so confirming is one
  keystroke. Deliberately not in this version - "reports, does not write"
  is what makes the first version safe to trust.
