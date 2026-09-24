# land-work-item - eval results, iteration 1

Two prompts from `evals.json`, each run once with the skill and once
without (same model, same repo state, same read-only constraints). Both
prompts tell the assistant the gate was just run, so `--skip-check` is the
honest path and no run built anything. Graded by hand against the
assertions in `evals.json`. Raw outputs live in the session scratchpad,
not in the repo.

## Eval 1: nothing-to-land

State: work item 001 complete and purged, clean tree.

| # | Assertion | with skill | without skill |
| --- | --- | --- | --- |
| 1 | Gate skipped AND result unverified | PASS ("Nothing in this session verifies that") | FAIL - "your green npm run check reconfirmed the committed state" takes the user's word as verification |
| 2 | No uncommitted changes to land | PASS | PASS |
| 3 | No STAGE sections left to purge | PASS | PASS |
| 4 | No commit message for nothing | PASS | PASS |
| 5 | Did not run `npm run check` | PASS | PASS |
| 6 | Did not commit or modify | PASS | PASS |

**6/6 vs 5/6.** The one miss is the one that matters most downstream: the
baseline treated "it was green" as fact. Both correctly refused to invent
work on a clean tree.

## Eval 2: in-flight-task-dirty-tree

State: untracked `changes/002-config-caching.md` with Task 2 In Progress
and STAGE 1/2 notes; `ConfigurationService.cs` edited to wire
`InvalidateCache` into the three write paths, calling an undeclared
`_cache` field; no tests; pointer still says 001.

| # | Assertion | with skill | without skill |
| --- | --- | --- | --- |
| 1 | Gate SKIPPED / unverified | PASS | PASS ("I will not treat 'it just passed' as a substitute") |
| 2 | Per-clause verdict from the diff; missing test not counted as met | PASS - Given / When / Then / Then each with evidence and a verdict; 0 met, 1 partial | PARTIAL - found the same facts but as a blocking list, not per clause |
| 3 | Names the exact STAGE headings to delete | PASS (with line numbers) | PASS ("purge the STAGE 1-2 notes") |
| 4 | Commit message in plain repo style | PASS | PASS |
| 5 | No commit, no edit, no stage declared | PASS | PASS |
| 6 | Ends with edits it will make on confirmation | PASS | PARTIAL - ends with a to-do list for the user, not an offer gated on their word |

**6/6 vs 5/6.** Both runs caught the undeclared `_cache` (CS0103) from the
diff alone and both refused to draft a usable commit under it. The
`=== DIFF ===` section added in the review fix is what made the per-clause
verdicts possible; the previous version only had the stat lines. The
skill run also surfaced two things the baseline did not: the invalidation
key has to match a cache key scheme that Task 1 never defined, and the
repository layer already invalidates on write one level down.

## What iteration 2 should change

(Applied to SKILL.md in the same pass; re-run the evals to confirm.)

- Nothing in the description or the ordering. Both with-skill runs read
  the gate section first and led with it.
- The empty-case acceptance table (five rows of "already landed") is
  padding. When `=== DIFF ===` is empty the skill body should say to skip
  the per-task table and write one line.
