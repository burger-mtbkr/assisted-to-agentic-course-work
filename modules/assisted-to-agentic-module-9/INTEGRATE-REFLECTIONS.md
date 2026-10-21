# Module 9 - Integrate & Reflect

Module 9 ships no `project/INTEGRATE.md`. Its `EXERCISE.md` ends with eight
debrief questions, answered below from building the Codebase Team and its live
repair run (`task-20261021-191836-ef1d`).

## Summary

**What I did:** Composed the Module 7 Doctor, the Module 8 Librarian and a new
Mechanic into `codebase-team/`. It is a deterministic pipeline with a human
approval gate, five validated handoff artifacts, an isolated workspace per run,
a trajectory log, and 23 coordination evals on a full run.

On a seeded `config-service` regression, the team diagnosed the failure,
briefed, waited, refused to patch without approval, patched only the approved
file, verified, and remembered the repair. After the review fixes a fresh live
run passed all 23 evals (87 tests before and after) and the original was untouched.

**How it went:** The contracts and the gate were straightforward. The value
showed up in the middle: the ambiguity of a failing test was settled by memory,
not by the model. The deterministic team tests found two real bugs the happy-path
live run never reached.

**What I learned:** Multi-agent coordination here is software architecture, as
the module says. One port, typed handoffs, an orchestrator that decides
ordering, permissions enforced in the mount rather than the prompt, and evals
that look at the middle of the run. "Agents talking" never needed to happen.

---

## 1. What did each agent know that the others did not?

| Agent | Knew | Did not know |
|---|---|---|
| Doctor | exactly what fails: test name, expected vs actual, file and line, and that lint is clean | which side is the contract |
| Librarian | why things are the way they are: the 409 decision note, the knowledge-graph warning, the Git history of the file, that tests guard it | what currently fails (it reads the diagnosis for that) |
| Mechanic | how to make the change and check it locally | anything outside the three handoffs |
| Human | whether the risk is acceptable, and the boundary | - |

The repair needed all four. The Doctor's evidence alone points equally at the
code and the test.

## 2. Which handoff artifact was most useful to the next specialist?

**The ContextBrief.** Its facts (the note's statement, the knowledge-graph
warning) and its constraints ("edit only `ErrorMiddleware.cs`"; "do not edit
the test: it encodes the contract") are what the Mechanic cited in its
rationale. They are also what the human based the approval on. The
DiagnosisReport was necessary, but it posed the question; the brief answered it.

## 3. Where did structure help more than free-form conversation?

- **Refusal.** `continue` before approval was refused deterministically by
  reading `approval.json`, not by an agent deciding it should wait.
- **Scope.** The Mechanic received three trimmed artifacts, not a transcript,
  and the mount allowed exactly one file.
- **Debugging.** `inspect` rebuilds the whole run - 28 events - from files
  alone. Any failure can be traced backward through artifacts:
  verification <- patch <- brief <- diagnosis <- approval.
- **Testing.** Typed artifacts and a port meant the whole workflow, including
  the Deep Agents Mechanic, ran in tests without a provider.

## 4. Did the human approval boundary prevent scope creep?

Yes, at three layers:

- **The approval** listed one path, with tests excluded on purpose.
- **The mount** would have refused anything else. A test proves an edit to the
  test file is refused, and the patch ends as "no change".
- **`finish_patch`** reverts any out-of-bounds change it finds in the diff and
  records it, as a test of a human's off-scope edit shows. The permission eval
  then fails "no out-of-bounds attempt", even though the final tree is clean.

The live Mechanic never tried. Its first move was to read the test, its second
to run the tests.

## 5. Was verification strong enough to trust the Mechanic's patch?

For the scenario, yes:

- **Independent checks.** The Doctor re-ran the service's own checks in the
  workspace. The test that failed in the diagnosis now passes, nothing else
  newly fails, and lint is clean.
- **The diff matches.** It is a one-line change that matches the brief.

Its limits are the unit suite's limits. `config-service`'s own memory says unit
tests do not prove the DynamoDB layer, and a repair there would need a live
run. The team cannot do that against AWS, by design. The verification report
should say so when the patch touches that layer; today it does not
distinguish.

## 6. If the run failed, which handoff failed first?

The live run did not fail. In the tests, each failure is traced to its first
weak handoff:

- **No approval:** the gate. `patch_blocked` is the first non-ok event.
- **Approval refused:** the human's record.
- **Out-of-bounds edit:** the patch. The mount refused it, so no change was
  made, and the outcome says "not repaired" without blaming verification.
- **Corrupted brief:** the ContextBrief artifact eval fails by name ("facts is
  empty") before anything downstream is trusted.
- **Out-of-order trajectory:** the trajectory eval ("approval before patch").

## 7. What would I change before using this on a larger codebase?

- **A cheaper workspace.** A full copy plus a clean .NET build per run is
  fine at this size; at scale, use `git worktree` or a cached build.
- **Check scoping.** Run the tests the Librarian links to the touched file
  first, then the full suite.
- **Multi-file boundaries.** Approve a module directory, with a size limit
  on the diff.
- **Real failures, not seeded ones.** Drive runs from CI failures, with the
  Doctor's diagnosis as the ticket.
- **A live Doctor and Librarian.** Use the full agents when diagnosis needs
  judgement (flaky tests, several failures), keeping the adapters as the
  default.
- **Verification that knows its blind spots.** Flag patches in untested
  layers as needing a live check.

## 8. When is a multi-agent structure worth the overhead, and when is one coding agent better?

**Worth it when:**

- **The change crosses a trust boundary.** It edits production code and
  needs a human gate.
- **The fix depends on knowledge the code does not hold.** Here it was a
  decision note.
- **A failure has to be explainable afterwards.**
- **The roles have different permissions.** Read-only diagnosis, memory
  writes, scoped edits.

**A single coding agent is better when:**

- **The task is exploratory, or the boundary is the whole repo.**
- **The fix is obvious from the failure** (a typo, an import).
- **Speed matters more than an audit trail.**

This scenario was small, and the overhead was visible: three artifacts and a
gate for a one-line change. But the one line was exactly the case where a lone
agent could have "fixed" the wrong side.

## What I'd carry forward

- Put the boundary in code at least twice: approval record, mount, post-hoc
  diff check.
- Evaluate the middle: order, permissions, evidence, not just "tests pass".
- Keep agents swappable behind a port. The human Mechanic and the Gemini
  Mechanic are interchangeable, and the tests use a scripted one.
