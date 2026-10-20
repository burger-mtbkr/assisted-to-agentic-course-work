---
name: remember-decision
description: "Use when asked to remember, record or note a decision, rationale or fact about config-service, or when the user corrects something previously remembered. Covers what is worth a note, the required fields, duplicate checks, and superseding old notes."
allowed-tools: remember_decision list_memory_notes read_memory_note retrieve_context read_file
---

# Remember a decision

A note is for what the source does not say: why something is the way it is,
a constraint, a correction. Facts the code states plainly do not need a note.

## Procedure

1. **Check for an existing note.** `list_memory_notes` (and `retrieve_context`
   on the statement). If a current note already says this, do not duplicate it.
   If a current note says something this contradicts or refines, this is a
   correction - go to step 4.
2. **Find support.** If the statement names code or docs, find them
   (`retrieve_context`, then `read_file`) so the note can cite paths. A
   statement only the user made is still worth keeping: cite `user` - the
   store adds the date, and caps confidence at 0.7 until a source backs it.
3. **Set confidence honestly.** 0.9 or higher: the source states it. About
   0.7: the user stated it and nothing contradicts it. 0.5 or lower: plausible
   but unverified - and say so in the rationale.
4. **Save.** `remember_decision` with a short `title`, the `statement` as one
   or two sentences, the `rationale` (why, and any trade-off), `sources`,
   `confidence`, `entities` (knowledge-graph term ids such as
   `configuration_item`, if any apply) and, for a correction, `supersedes`
   with the old note ids.
5. **Confirm** the note id, what it cites, and anything it superseded. If the
   source contradicts the statement, save nothing and say what the source
   shows instead.
