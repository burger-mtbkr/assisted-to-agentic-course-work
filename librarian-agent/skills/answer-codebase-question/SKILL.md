---
name: answer-codebase-question
description: "Use for any question about config-service: what something is, where it is implemented or tested, why it works the way it does, or what changed and when. Covers which memory to consult in what order, how to verify, and how to cite and state gaps."
allowed-tools: retrieve_context read_file grep git_log git_show file_history read_memory_note
---

# Answer a codebase question

## Procedure

1. **Retrieve.** Call `retrieve_context` with the question in your own words.
   Read its `recommended_context`, `memories` and `gaps` before anything else.
2. **Route by question type.**
   - *What / where* - verify in the recommended source files (`read_file`
     around the lines given). Follow `graph_expansion` edges to tests
     (`tested_in`) and docs (`documents`).
   - *Why* - look for a current note in `memories` first; then the docs the
     graph points to (`context/*.md`); then Git: `file_history` on the main
     file, `git_show` on the commit whose subject matches.
   - *What changed / when* - `git_log` (for the codebase or a path) and
     `git_show`; the index does not cover history.
3. **Verify before you assert.** A note or a semantic hit is a lead, not an
   answer. Confirm the claim in the source; if source and note disagree, the
   source wins and you say the note is out of date.
4. **Answer** in this shape:

```markdown
<answer, two to six sentences or a short list>

**Sources**
- source: `path` lines a-b - what it shows
- note: `note-id` (confidence) - what it records
- git: `abc1234` (date) - what it changed

**Gaps and uncertainty**
- <what the evidence does not cover, notes marked uncertain, what you did not verify>
```

## Guardrails

- Never cite the index itself; cite the file, note or commit it led you to.
- Superseded notes are history, not current fact. Only use them when the
  question is about what was believed before - and say they are superseded.
- If retrieval returns nothing relevant, say so and search (`grep`) once with
  the exact identifiers before concluding the codebase does not cover it.
