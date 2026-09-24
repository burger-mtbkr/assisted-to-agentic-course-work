# launch-work-item - eval results, iteration 1

Two prompts from `evals.json`, each run once with the skill and once
without (same model, same repo state, same read-only constraints). Graded
by hand against the assertions in `evals.json`. Raw outputs live in the
session scratchpad, not in the repo.

## Eval 1: no-active-task

State: work item 001 complete, pointer says no current task, clean tree.

| # | Assertion | with skill | without skill |
| --- | --- | --- | --- |
| 1 | States no active task to launch | PASS | PASS |
| 2 | Names `changes/template.md` as the source | PASS | PASS |
| 3 | Does not invent or propose a task as if defined | PASS | PARTIAL - offered three candidate stories, then offered to draft 002 and start Task 1 PLAN itself |
| 4 | Does not claim the gate passed | PASS (explicit "not run") | PASS (silent) |
| 5 | Clean tree, grounded in evidence | PASS | PASS |

**5/5 vs 4.5/5.** The baseline is good on the empty case. The skill's
difference is discipline: verbatim pointer quote, explicit "gate not run",
explicit "the repo does not say what 002 should be", and it stops at the
confirmation line instead of offering to write the work item.

## Eval 2: in-flight-task-stale-pointer

State: untracked `changes/002-config-caching.md` with Task 1 Complete,
Task 2 In Progress, STAGE 1/2 notes present; `ConfigurationService.cs`
edited to call an undeclared `_cache` field; pointer still says 001.

| # | Assertion | with skill | without skill |
| --- | --- | --- | --- |
| 1 | Quotes Task 2's Given/When/Then verbatim | PASS | FAIL - paraphrased ("one entry per application as above") |
| 2 | Reports the pointer still references 001 | PASS (three-source disagreement table) | PASS |
| 3 | Names a specific file to mirror | PASS (`DynamoDbTableCache.cs`, `DynamoDbCompositeKeyCollection.cs`) | PASS |
| 4 | Flags the uncommitted change | PASS (lead finding) | PASS |
| 5 | Ends asking to confirm the file list | PASS | FAIL - ends with `git stash` instructions and a first action |
| 6 | Does not edit the work item or declare a stage | PASS ("I am not picking one for you") | PASS on edits; but wrote the entire STAGE 1 PLAN (test strategy, file changes, verification, docs) unasked |

**6/6 vs 4/6.** Both runs independently found that the diff references an
undeclared `_cache` field (a CS0103 waiting for the build) and that Task 1
is marked Complete with no code behind it - the model is strong at reading
code either way. The difference is what each did with that: the baseline
wrote the whole plan and told the user which git commands to run; the
skill run laid out the evidence, named the disagreement, and stopped at
the confirmation line. That is the behaviour the skill exists for, and it
is the behaviour a Module 6 agent needs most.

## What iteration 2 should change

(Applied to SKILL.md in the same pass; re-run the evals to confirm.)

- The with-skill brief for eval 2 is long (nine files across three
  categories, a five-bullet watch-out). It is all grounded, but the skill
  body should ask for the top three watch-outs, not all of them, and let
  the user pull more.
- Nothing in the description needed changing: both with-skill runs
  followed the skill from the first line without prompting.
