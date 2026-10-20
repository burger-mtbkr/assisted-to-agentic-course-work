---
name: prepare-change-context
description: "Use when asked to find or prepare context for a future change - for a developer or another agent such as a Mechanic: what to read, which tests guard it, which decisions constrain it, what is missing."
allowed-tools: retrieve_context read_file grep git_log file_history read_memory_note
---

# Prepare context for a change

The reader is about to edit code. Give them the smallest set of things to
read, the constraints they must not break, and what nobody knows yet.

## Procedure

1. **Retrieve** with the change described in domain words
   (`retrieve_context`). Then retrieve once more with the exact type or file
   names the first result surfaced, if any.
2. **Walk the graph** from the matched terms: `implemented_in` files, their
   `tested_in` tests, the docs that `documents` them, notes that `explains`
   them.
3. **Read the top recommended files** far enough to name the exact place a
   change would go, and the tests that would need to change with it.
4. **Check history** for the main file (`file_history`): recent churn or a
   past fix is a constraint worth knowing.
5. **Report**:

```markdown
**Read first** - files with line ranges, and why each matters
**Tests that guard it** - test files, and what they pin down
**Constraints** - decisions and warnings (note ids, doc lines, knowledge-graph warnings)
**Likely edit boundary** - the narrowest set of files a first change should touch
**Gaps** - missing tests, missing decisions, unverified assumptions
**Semantic matches / graph relationships** - the evidence behind the above, briefly
```
