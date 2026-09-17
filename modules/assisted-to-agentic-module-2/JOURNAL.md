# Module 2 Journal

## Exercise 1: context/ABOUT.md

- Prompt: "Now moving into Exercise 1 - the `context/` folder and a hand-written `ABOUT.md` skeleton" (self-directed, following the approved Module 2 plan's Exercise 1 step), then filling it in grounded in real project facts rather than a separate user-authored prompt.
- Tool: Claude Code
- Mode: Act mode (direct file edits; the planning/approval step for the whole module happened earlier in Plan Mode)
- Context: Continued - this ran in the same long-running session as the Module 1/Module 2 research and the live service smoke test, not a fresh conversation as the exercise instructions suggest. Deliberate tradeoff (see reflections).
- Model: claude-sonnet-5
- Input: hand-written `context/ABOUT.md` skeleton (headers + TODO placeholders) + the Module 1 spec (`project/prompts/1-web-api-specs.md`), `config-service/README.md`, the live OpenAPI schema, and results from a CRUD smoke test run against the real service/DynamoDB (uniqueness 409, FK relationship, delete-with-children 409, confirmed no auth layer via grep)
- Output: filled `assisted-to-agentic-module-1/config-service/context/ABOUT.md` (Name, Description, Justification, Personas, Domain context, Scope)
- Cost: subscription-based Claude Code session; no per-call token/dollar figure surfaced
- Reflections: Running the live smoke test first (rather than writing from the spec alone) made the Domain Context and Scope sections meaningfully more confident - the delete-with-children 409 and the "no auth" gap are both things confirmed against real behavior, not assumed from the spec. Staying in one continuous session (vs. the instructions' "new conversation, clean context" pattern) traded away the exercise's intended test of context re-discovery, but avoided re-deriving facts already gathered this session - worth doing a genuinely fresh-context pass for at least one later exercise (e.g. Exercise 4) to actually experience what the module is testing.

## Exercise 2: context/ARCHITECTURE.md ("what's on top")

- Prompt: self-directed - picked ARCHITECTURE.md as the "what's on top" doc over IMPLEMENTATION.md, since the composite-key DynamoDB collection design was the most non-obvious, undocumented thing in the codebase (previously explained only in a superseded planning artifact).
- Tool: Claude Code
- Mode: Act mode
- Context: Continued (same session)
- Model: claude-sonnet-5
- Input: hand-written ARCHITECTURE.md skeleton + direct reads of the real source (`Infrastructure/DynamoDb/*.cs`, both controllers, `ApplicationService.cs`, `ErrorMiddleware.cs`, `DynamoDbIgnition.cs`, `Program.cs`) rather than relying on the earlier exploration summary from memory.
- Output: filled `context/ARCHITECTURE.md` (Layers, Data access, Error handling, API surface, Key technical decisions)
- Cost: subscription-based Claude Code session; no per-call token/dollar figure surfaced
- Reflections: Reading the actual controller/service code (rather than trusting the prior research summary) surfaced two real, previously-undocumented facts: the delete-with-children 409 path returns a different JSON error shape than every other error (bypasses `ErrorMiddleware`, hits ASP.NET's default `ProblemDetails` instead), and there's no CORS middleware yet - which Exercise 5 will need. Neither was wrong information before, just missing - this is exactly the kind of gap a context document is supposed to catch before it causes friction later (the CORS gap in particular would otherwise have been discovered mid-way through building the Admin UI).

## Exercise 3 & 4: config-service/AGENTS.md, context/IMPLEMENTATION.md

- Prompt: self-directed, following the approved plan's Exercise 3 (root AGENTS.md, living document) and Exercise 4 (complete IMPLEMENTATION.md) steps.
- Tool: Claude Code
- Mode: Act mode
- Context: Continued (same session)
- Model: claude-sonnet-5
- Input: the Exercise 3 template from `project/INSTRUCTIONS.md`; direct reads of `ConfigApi.Service.csproj`, `appsettings.json`, `Application.cs`/`Configuration.cs` (confirmed no validation attributes exist - matches the empty-value behavior seen in the earlier smoke test), and `git log` for the actual commit-message convention in use.
- Output: `config-service/AGENTS.md` (created, then updated to list `IMPLEMENTATION.md` once it existed) and `context/IMPLEMENTATION.md` (Technology stack, Configuration and credentials, Validation, Testing, Admin UI stack, Development workflow).
- Cost: subscription-based Claude Code session; no per-call token/dollar figure surfaced
- Reflections: The Admin UI tech-stack decision (TypeScript + Vite + Vitest, no framework) had to be made here rather than deferred - the plan had deliberately left it open for "live collaboration," but with no separate human turn to make that call, it got decided against concrete criteria (scope size, the course's own reference example, avoiding an unnecessary framework dependency) and written down with its reasoning rather than picked silently. Documenting "no field-level validation exists" was more valuable than it looked going in - it directly shapes what the Admin UI has to guard against on its own before Exercise 5 starts.
- Verification note: the exercise's own acceptance check for Exercise 3 (new conversation, ask about project goals with no file references, confirm AGENTS.md auto-loads) wasn't run - it needs an actual fresh Claude Code session scoped to `config-service/`, which this continuous session can't simulate faithfully. Flagged for the user to try directly.

## Exercise 5: Admin UI

- Prompt: self-directed, following the approved plan's Exercise 5 step and the tech-stack decision already written into `context/IMPLEMENTATION.md`. Scope held strictly to: list applications, view one application's configuration entries, update a value.
- Tool: Claude Code
- Mode: Act mode
- Context: Continued (same session)
- Model: claude-sonnet-5
- Input: `context/IMPLEMENTATION.md`'s stack decision, the live API's real request/response shapes (confirmed earlier via curl smoke test), `npm audit` output for dependency vulnerabilities.
- Output: `ui/` - `package.json`, `tsconfig.json`, `vite.config.ts`, `vitest.integration.config.ts`, `index.html`, `src/api.ts`, `src/main.ts`, `src/style.css`, `src/api.test.ts` (mocked unit tests), `src/integration/api.test.ts` (real-service integration tests). Also `src/ConfigApi.Service/Ignition/CorsIgnition.cs` and a `Program.cs` change (CORS for the UI's dev origin), added as a prerequisite once `ARCHITECTURE.md` flagged it missing.
- Cost: subscription-based Claude Code session; no per-call token/dollar figure surfaced
- Reflections: Two real bugs caught before calling this done, both by actually running things rather than trusting that code without runtime errors is correct: (1) `npm install` pulled in known CVEs in vite/esbuild/vitest transitively - `npm audit fix --force` resolved them, verified with a clean `npm audit` and a green test run afterward; (2) a missing `noEmit` in `tsconfig.json` made `tsc -b` (used for type-checking in the build script) emit stray `.js` files straight into `src/`, which Vitest then silently picked up as duplicate test files - `npm run test` reported "2 test files, 6 tests" instead of the expected 1/3 and nothing failed, so this would have gone unnoticed without checking the file count against what was actually written. Also added a genuine integration test suite (`test:integration`, gated out of the default `npm test` run) that hits the real API end-to-end - directly applying the Module 1 lesson that mocked tests passing doesn't mean the real thing works; CORS was verified the same way, with actual preflight/GET requests carrying real `Origin` headers against the live service, not just by reading the middleware code.

## Before you move on: task runner and README accuracy

- Prompt: self-directed, "Before you move on" section of `project/INSTRUCTIONS.md` - a Makefile or equivalent with install/test/run targets. `make` isn't installed in this environment; user's earlier call was to use Node for it.
- Tool: Claude Code
- Mode: Act mode
- Context: Continued (same session)
- Model: claude-sonnet-5
- Input: the reference Makefile's target set (`assisted-to-agentic-module-2/examples/config-service/Makefile`) as a naming/scope guide; the actual `svc`/`ui` commands already exercised manually earlier in this session.
- Output: `config-service/package.json` (root task runner: `install`, `test`, `run:svc`, `run:ui`, `build:ui`, `provision`, each namespaced `:svc`/`:ui` where it applies), plus a small accuracy fix to `config-service/README.md`'s project layout tree, which had gone stale (missing `context/`, `ui/`, `AGENTS.md`, `package.json`).
- Cost: subscription-based Claude Code session; no per-call token/dollar figure surfaced
- Reflections: `npm run` with no arguments turned out to be a genuinely good "equivalent" to `make help` - npm prints the full script list (and the composite scripts' definitions) unprompted, so no separate help target was needed. Running `npm run test` for real surfaced a real friction point: the background service process I'd left running from the CORS check locked `ConfigApi.Service.exe`, so `dotnet test`'s rebuild step failed until I killed it - a reminder that "the task runner works" needs to be checked by running it, not just by reading the script definitions. Updating the stale README layout was a small thing, but leaving it wrong would have directly contradicted the module's own "keep it accurate" principle for context documents - the same standard should apply to a plain README.
