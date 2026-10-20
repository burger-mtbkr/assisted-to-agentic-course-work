---
name: repair-issue
description: "Use for every repair: how to read the diagnosis, the context brief and the approval, make the smallest change inside the approved paths, check it, and report the patch."
allowed-tools: read_file grep glob ls edit_file write_file run_tests
---

# Repair an issue

You have three handoffs, quoted in the request: the Doctor's diagnosis (what
fails, with evidence), the Librarian's context brief (facts, constraints,
gaps), and the human's approval (the paths you may edit, the commands you may
run). Nothing outside them is part of the job.

## Procedure

1. **Read the evidence, not just the summary.** Open the failing test at the
   line the diagnosis gives, and the code it names. Confirm you see the same
   disagreement the diagnosis describes.
2. **Decide which side is the contract.** The context brief's facts and
   constraints say which behaviour is intended (remembered decisions, the API
   contract, knowledge-graph warnings). Change the side that is wrong. If the
   brief and the evidence disagree, or the fix needs a path you were not
   approved for, stop and say so - do not edit around the boundary.
3. **Make the smallest change.** One `edit_file` with an exact `old_string`
   is usually enough. Do not reformat, rename or "tidy" anything else.
4. **Check it, if approved.** If `run_tests` is available, run it once and
   read the result. A still-failing check means the repair is not done.
5. **Report** with this JSON block as the last thing in your reply:

```json
{"intent": "what the change does, in one sentence",
 "rationale": "why this side was wrong, citing the brief's facts",
 "risks": ["anything the reviewer should know"]}
```

## Guardrails

- Never edit a test to make it pass unless the approval names that test file.
- Never claim the repair works unless a check you ran says so.
- A refused write means the path is not approved: stop, do not try another path.
