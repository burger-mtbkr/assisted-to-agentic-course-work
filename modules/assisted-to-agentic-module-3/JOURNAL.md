# Module 3 Journal

## Entry 1: Scaffold procedural/episodic memory, quality gates, first work item

- **Prompt**: "now that you have completed module 2 start exploring module 3
  and determine what you need to do end to end to make it work"
- **Tool**: Claude Code (VS Code extension)
- **Mode**: Plan mode (`EnterPlanMode`/`ExitPlanMode`) for the design, then
  direct file edits and shell commands for execution
- **Context**: `modules/assisted-to-agentic-module-3/` (curriculum: README.md,
  project/INSTRUCTIONS.md, project/INTEGRATE.md, the Python/Make worked
  example) and `config-service/` (the actual
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
- **Cost**: 11% of the account's 5-hour Claude usage limit (subscription
  session; no per-call dollar figure surfaced, this is the rolling-window
  usage metric Claude Code reports).
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

## Entry 2: Execute Exercise 4 end to end - all five feature-flag tasks

- **Prompt**: "do it" (start Task 1's PLAN), then mid-session "do everythign
  needd for module 3", then "do what the unstutions say. Follow a scope,
  plan, implement, verify and close approach" (resolving an open question
  about lint/format scope from Entry 1 by pointing back at INSTRUCTIONS.md's
  literal text)
- **Tool**: Claude Code (VS Code extension)
- **Mode**: Direct execution - no plan-mode gate this time; the four-stage
  workflow scaffolded in Entry 1 (`context/WORKFLOW_STATUS.md`) supplied the
  structure instead, run once per task without stopping for a stage-gate
  confirmation each time (explicit user direction - see Reflections)
- **Context**: `config-service/`
  (`changes/001-feature-flags.md`, the whole `Configurations` vertical
  slice as the pattern to mirror, `ui/`, `infra/`), plus the real AWS
  account (DynamoDB, IAM) and a real headless-Chrome session for UI
  verification
- **Model**: Claude Sonnet 5 (`claude-sonnet-5`)
- **Input**: Filled Task 1's PLAN section and got it read back; the user
  then asked for the remaining four tasks and the workflow's REFLECT/COMMIT
  stages to be run without a stage-gate stop at each transition. Along the
  way, asked the user two things that were genuinely their call: how to
  handle an AWS IAM permission gap blocking the new `flags` table (fix it
  directly via CLI, tag the new resource for course cleanup) and whether to
  push each task's commit individually or batch pushes to the end (batch).
- **Output**: All five tasks of `changes/001-feature-flags.md` complete, one
  commit each - domain model + migration (`0003_CreateFlagsTable.cs`,
  `Models/Flags/Flag.cs`), full backend CRUD (`Controllers`/`Services`/
  `Repositories`/`Exceptions` under `Flags`, DI wiring, 22 new unit tests),
  Admin UI (`Feature Flags` table on the existing configuration screen,
  `listFlags`/`updateFlag` in `api.ts`), the `README.md` client-consumption
  section, and a final accuracy pass over `context/ABOUT.md`,
  `ARCHITECTURE.md`, `IMPLEMENTATION.md`. Extended the
  `config-service-local-dev` IAM policy to cover the new `flags` table ARN;
  fixed a real bug found while writing Task 4's docs
  (`ApplicationService.DeleteAsync`'s delete-with-children guard only
  checked configuration entries, not flags - now checks both). Every change
  touching DynamoDB or the UI was verified against the real API/database or
  a real browser session, not just the mocked unit suite. Work item purged
  to acceptance-criteria-only per the workflow's own discipline;
  `modules/assisted-to-agentic-module-3/INTEGRATE-REFLECTIONS.md` written answering
  `project/INTEGRATE.md`'s four questions; `context/ENV_SCRIPTS.md` updated
  with the IAM/off-script gap this session surfaced.
- **Cost**: Not tracked for this entry.
- **Reflections**: The main tension worth naming for next time:
  `context/WORKFLOW_STATUS.md` says explicitly "ONLY the user decides when
  a stage is complete... the assistant MUST NOT declare stage completion,"
  and this session didn't follow that after the first task - the user's
  "do everything needed for module 3" was taken as authorization to
  self-drive all four stages per remaining task. That was the right call
  given the explicit instruction, but it means this run tested "can the
  assistant execute the four stages thoroughly and correctly" rather than
  "does the assistant respect the human-in-the-loop gate," which is a
  different (and arguably more important) property of the workflow. Two
  things justified the extra verification overhead the workflow demands:
  the IAM gap would have silently blocked the feature entirely if the
  work had stopped at "unit tests pass," and the delete-guard bug was
  invisible to every existing test (all mocked) and would have shipped
  silently without the live DynamoDB checks. `context/IMPLEMENTATION.md`
  itself predicted exactly this failure mode from a Module 1 incident, and
  it held up a second time.

## Entry 3: Cross-module compliance audit of Modules 1-3

- **Prompt**: "Reivew the workspace. we have already compleed modules 1 - 3.
  I want you to review hwat was done against theinstrcutions and examples. I
  want you to ensure we have 100% correct." Then, after a first pass and an
  honest admission that the examples had only been read secondhand: "Fix what
  you need", "are you happy thsi si good enough?", and "thsi it not good
  enough. keep fixing until you are 100% satisfied do not stop until done its
  all tsted committted and pushed"
- **Tool**: Claude Code (VS Code extension)
- **Mode**: Direct execution - a review/repair pass, not a workflow task, so
  no work item was opened under `changes/`
- **Context**: Clean session. All three modules' `README.md`,
  `project/INSTRUCTIONS.md` and `project/INTEGRATE.md`; the curriculum
  `examples/` for each (read directly this time, in particular Module 3's
  worked `WORKFLOW_STATUS.md`, `ENV_SCRIPTS.md`, `docs/template.md` and
  `docs/001-feature-flags.md`, and Module 2's example `AGENTS.md` and
  `context/`); the whole of `config-service/`; and `git log`
- **Model**: Claude Opus 5 (`claude-opus-5`)
- **Input**: The three modules' curriculum material and student artifacts,
  plus the live service running against the real DynamoDB tables in
  `ap-southeast-6`
- **Output**: Four commits - `85e0128` (recover the git-ignored Module 1
  prompts, populate Module 3's empty `prompts/`, simplify the `.gitignore`
  module block, document the `project/` trap in the repo `AGENTS.md`),
  `371cffd` (carry the last two orphaned Module 1 conventions into
  `context/`), `d33f16e` (remove the dead `ConfigurationNotFoundException`),
  `c5789f1` (fix the coverlet exclusion filters, add 8 tests, wire
  `npm run coverage`, correct the coverage claims in `README.md` and
  `context/IMPLEMENTATION.md`, harden `config-service/AGENTS.md`, add a
  Prerequisites section to `ENV_SCRIPTS.md`)
- **Cost**: Not separately metered in this environment.
- **Reflections**: Two findings mattered, and both were invisible from
  inside the modules themselves.

  The first was a git problem, not a code problem. The `modules/` reorg had
  moved Module 1's `prompts/` folder into `project/`, which `.gitignore`
  excludes wholesale as curriculum material - so `1-web-api-specs.md`,
  `2-web-api-prompt.md` and `3-web-api-plan.md` were sitting on disk,
  looking perfectly present in the editor, while being absent from every
  clone of the repo. The module's own `EXERCISE-PLAN.md` had written down
  the correct rule ("student artifacts live directly under the module root,
  not inside `project/`") back in Module 1, and the reorg silently broke it
  three commits later. Worth noting for the course's own purposes: "the file
  is there" and "the file is committed" are as different as "tests pass" and
  "the feature works", and the same kind of check catches both.

  The second was a quality-gate problem. `coverlet.runsettings` listed
  exclusions that matched nothing - the `Exclude` filters were missing the
  namespace prefix on the type half, and `ExcludeByFile` used `%2c`
  comma-escaping that only works on the MSBuild `/p:` command line. A filter
  that binds to nothing fails silently: the report still generates, still
  looks authoritative, and the excluded classes are quietly still in it.
  Module 1's journal recorded "every business-logic class shows 100% line
  coverage" read off exactly such a report; re-measuring with corrected
  filters gave 33.4% overall and 73-82% on the three service classes. The
  gaps were small and real (untested pass-throughs, and the blank-key branch
  of the key validators, which the existing `"bad key!"` cases never
  reached), and eight tests closed them - 87 tests, 100% line and branch
  across every measured class, this time verified rather than asserted.

  Reading the examples directly rather than through the earlier journals'
  account of them changed one thing materially. Module 3's example
  `AGENTS.md` makes the workflow document mandatory - "read it before
  planning any work" - where ours said only "load files selectively." That
  is precisely the failure mode Entry 2 of this journal confesses to: the
  assistant self-driving all four stages past a rule the workflow document
  states in capitals. The rule was written down, but it was written down
  somewhere the assistant had explicit permission not to read. Moving it to
  the front door is a small edit and probably the most useful change in this
  whole pass.

  On verification: the earlier rounds of this audit reported "verified
  working" on the strength of `npm run check`, which is the mocked suite -
  the exact thing Module 1's retro says proves nothing about the real
  system. That was the right criticism to accept. The final round ran the
  service against real DynamoDB: 23/23 CRUD and error scenarios including
  the delete-with-children guard for both children, CORS preflight from the
  UI origin, the root -> `/scalar` redirect, `openapi.json` byte-identical
  to the live document, and the integration suite green. The tables were
  snapshotted beforehand and compared afterwards - no leftover test records,
  no pre-existing data touched.
