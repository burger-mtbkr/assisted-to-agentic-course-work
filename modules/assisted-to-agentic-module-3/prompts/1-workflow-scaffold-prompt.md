Prompt used to scaffold the procedural/episodic memory documents, quality
gates, and the first work item (Exercises 1-3). Transcribed from the
`JOURNAL.md` Entry 1 record of the live session.

---

now that you have completed module 2 start exploring module 3 and determine
what you need to do end to end to make it work

---

Notes on how this ran: issued in Plan mode. The assistant read
`project/INSTRUCTIONS.md` (not just `README.md`) plus the module's
Python/Make worked example, cross-checked both against the real
`config-service/` stack (.NET 10 + DynamoDB, TypeScript/Vite UI, npm-script
task runner, no Makefile, no CI), and came back with four scoping questions
before writing anything:

1. Work item location - `changes/` or `docs/`?
2. Commit message style - plain `"Module N: ..."` or conventional commits?
3. Branching - stay on `main`, or a feature branch per work item?
4. How literally to implement the new lint/format quality gates, given
   neither a Makefile nor a UI linter existed yet?

Answers: `changes/`, plain style, stay on `main`, implement the gates for
real. Plan approved before any file was touched.
