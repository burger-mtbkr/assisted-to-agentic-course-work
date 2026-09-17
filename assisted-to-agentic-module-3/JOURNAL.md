# Module 3 Journal

## Entry 1: Scaffold procedural/episodic memory, quality gates, first work item

- **Prompt**: "now that you have completed module 2 start exploring module 3
  and determine what you need to do end to end to make it work"
- **Tool**: Claude Code (VS Code extension)
- **Mode**: Plan mode (`EnterPlanMode`/`ExitPlanMode`) for the design, then
  direct file edits and shell commands for execution
- **Context**: `assisted-to-agentic-module-3/` (curriculum: README.md,
  project/INSTRUCTIONS.md, project/INTEGRATE.md, the Python/Make worked
  example) and `assisted-to-agentic-module-1/config-service/` (the actual
  student project this module extends in place)
- **Model**: Claude Sonnet 5 (`claude-sonnet-5`)
- **Input**: Read Module 3's actual exercise steps (INSTRUCTIONS.md, not
  just the generic README) and its worked example's `ENV_SCRIPTS.md`,
  `WORKFLOW_STATUS.md`, `template.md`, and `001-feature-flags.md`, then
  cross-checked all of it against the real project - .NET 10 + DynamoDB API,
  TypeScript/Vite Admin UI, npm-script task runner, no Makefile, no CI
  (versus the example's Python/FastAPI + Make). Asked the user four scoping
  questions where the example and the existing repo disagreed: work item
  location (`changes/` vs `docs/`), commit message style (plain vs
  conventional commits), branching (stay on `main` vs feature branches per
  work item), and how literally to implement the new lint/format quality
  gates given neither a Makefile nor UI linter existed yet. Wrote an
  implementation plan reflecting the answers and got explicit approval
  before touching any files.
- **Output**: `context/ENV_SCRIPTS.md` and `context/WORKFLOW_STATUS.md`
  (new); `AGENTS.md`, `README.md`, and `context/IMPLEMENTATION.md` updated
  to reference them; `changes/template.md` and `changes/001-feature-flags.md`
  (first work item, Exercise 3, stage-tracking sections left blank per the
  exercise's instructions); real lint/format tooling added where none
  existed - `dotnet format` wired into `lint:api`/`format:api` (no new
  dependency, ships with the .NET SDK), ESLint (flat config) + Prettier
  added as dev dependencies to `ui/` with matching npm scripts; `lint`,
  `format`, `format:check`, `type-check`, and `check` scripts added to the
  root `package.json` task runner; fixed the four UI source files Prettier
  flagged (all line-wrap only, `printWidth: 80`); scaffolded this module's
  `prompts/` and `JOURNAL.md`. Verified with `npm run check` (test + lint +
  format:check + type-check, all green) and a clean `npm audit --prefix ui`.
- **Cost**: Not separately metered in this environment (subscription-based
  Claude Code session, no per-call token/dollar figure surfaced).
- **Reflections**: The module's own worked example didn't match the
  project's actual stack at almost any level - Make vs npm scripts, Python
  vs .NET/TypeScript, no linter vs needing one added from scratch - so
  "adapt the commands" (INSTRUCTIONS.md's own caveat) meant redesigning the
  quality-gate surface, not just renaming `make test` to `npm run test`.
  The most useful find wasn't in the module 3 materials at all: `infra/README.md`,
  written back in Module 1, already reserved migration `0003` for a `flags`
  table with the exact key schema this feature needs - proof that the
  "flag a decision as a note for later" discipline from earlier modules
  paid off directly here. Deliberately did not run Exercise 4 (execute the
  workflow) or Exercise 5 (reflect) in this pass:
  `context/WORKFLOW_STATUS.md` states "only the user decides when a stage
  is complete," and Exercise 4 is written as a live, turn-by-turn exercise
  for the user's own conversation - running it unattended here would have
  skipped the actual point of the exercise.
