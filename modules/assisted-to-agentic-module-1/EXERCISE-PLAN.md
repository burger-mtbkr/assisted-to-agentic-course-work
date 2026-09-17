# Module 1 Exercise — Full Plan (Steps 1-8)

## Context

The student (you) is doing the Module 1 "Configuration API Service" exercise defined
in `assisted-to-agentic-module-1/project/INSTRUCTIONS.md`. That document assumes
Cline + OpenRouter + Claude Sonnet 4; per your direction, **Claude Code is used
throughout instead** — same Plan-then-Act discipline, same journal template, just a
different tool/model recorded in each journal entry (Tool: Claude Code, Model:
`claude-sonnet-5`).

Git is already initialized at the repo root, so Step 1's `git init .` is not
needed. All student-authored artifacts (`prompts/`, `JOURNAL.md`, `AGENTS.md`,
`config-service/`) live directly under `assisted-to-agentic-module-1/` — not inside
`project/`, which the repo's own [AGENTS.md](../AGENTS.md) designates read-only
curriculum reference material shared by all modules.

Step 2 requires `prompts/1-web-api-specs.md` to name a real, deployable database.
Your first pick (`json-flatfile-datastore`) is a JSON flat-file store, which the
exercise explicitly excludes ("not in-memory or file-based storage"). You switched to
DynamoDB instead, which also matches what your reference project `income-service`
(github.com/burger-mtbkr/income-service) uses in production, and you've authorized
provisioning a real (free-tier, on-demand billing, no backups) table for it in your
AWS account.

This plan covers the entire exercise end-to-end (Steps 1-8) so it can be executed in
a fresh session without re-deriving these decisions.

## Decisions already made (carry these into every step below)

- **Stack**: C#, .NET 10, ASP.NET Core Web API (`Microsoft.NET.Sdk.Web`), MVC
  controllers (not Minimal APIs).
- **Architecture**: Controller → Service → Repository. One `IDynamoDbCollection<T>`-
  style repository per entity. DI registration grouped into `Ignition/*.cs` static
  classes (e.g. `DynamoDbIgnition`, `ServicesIgnition`, `RepositoryIgnition`).
  Domain-grouped `Exceptions/`. `GlobalUsings.<Layer>.cs` per layer.
  All patterned after `income-service`.
- **Key dependencies** (from `income-service`'s actual `.csproj`, plus `DotNetEnv`):
  `AWSSDK.DynamoDBv2`, `Serilog.AspNetCore` (logging), `Microsoft.AspNetCore.OpenApi`
  + `Scalar.AspNetCore` (API docs/UI), `xunit` + `Moq` + `coverlet.collector`/
  `coverlet.msbuild` (testing/coverage), `DotNetEnv` (loads AWS credentials from a
  local `.env` file at startup). `Nullable`/`ImplicitUsings` enabled,
  `TreatWarningsAsErrors`.
- **Database**: AWS DynamoDB, real account (not DynamoDB Local/in-memory) — satisfies
  "must be deployable". Two tables to start: `applications` and `configurations`
  (one table per entity, matching `income-service`'s pattern, not single-table
  design). `configurations` keyed by `applicationId` (partition key) + `configKey`
  (sort key) — the DynamoDB equivalent of a relational FK to `applications`.
  Billing mode: **on-demand (`PAY_PER_REQUEST`)** — zero-baseline, pay only for
  actual requests. **Point-in-time recovery: disabled** (no backups, per your
  instruction) — also removes PITR's incremental storage cost. At course-exercise
  volume this is effectively $0 under the always-free tier; only sustained heavy
  traffic would incur cost, which won't happen here. Region: **`ap-southeast-6`
  (Asia Pacific / New Zealand)** — confirmed via the AWS account as a real, opted-in
  region with DynamoDB available; confirm before creating anything, since table
  creation is a real infrastructure mutation.
- **AWS credentials**: supplied via a local `.env` file at the repo root (never
  committed — must be in `.gitignore`), loaded into process environment variables at
  startup via `DotNetEnv`, then picked up by the standard AWS SDK credential chain.
  Commit a `.env.example` with the required variable names and no real values.
- **Data access / migration strategy**: no SQL-style migrations (NoSQL). Table +
  key-schema definitions live in the repo as a small versioned provisioning script
  (`infra/` or similar) that creates/updates tables — the DynamoDB analogue of the
  course example's numbered SQL migrations folder.
- **Testing**: `xunit` + `Moq`, tests colocated in a sibling `*.UnitTests` project
  mirroring the source tree (`Controllers/`, `Services/`, `Repositories/`).
- **API surface**: `applications` and `configurations` resources under `/api/v1`,
  REST CRUD (mirroring the course example's shape, adapted to this architecture).
  The service must be fully workable end-to-end against the real DynamoDB tables —
  not just scaffolded — with `Scalar.AspNetCore` (Swagger UI replacement) enabled in
  the dev environment for manually exercising every endpoint.
- **Looking ahead (Module 3 flags)**: a `flags` table keyed by `applicationId`
  (partition key) + `flagKey` (sort key) is the DynamoDB-native equivalent of "a
  `flags` table with a foreign key to `applications`" the course instructions call
  out — worth keeping in mind when finalizing the key-schema decisions above.

## Reference material already gathered (don't re-derive)

- `income-service` structure and stack confirmed directly from its GitHub repo
  (Controllers/Services/Repositories layout, `Ignition/*.cs` DI pattern,
  `GlobalUsings.<Layer>.cs`, domain-grouped `Exceptions/`, `.csproj` package list,
  `global.json` pinning `net10.0`).
- `json-flatfile-datastore` confirmed via its GitHub description to be a JSON
  flat-file store — excluded by the exercise's own spec requirements.
- Course's reference spec/example (`examples/web-api-example-specs.md`,
  `examples/config-service/`) uses Python/FastAPI/Postgres — useful only as a
  structural template for what the spec file should cover, not as a tech choice.
- `assisted-to-agentic-module-1/` currently contains only curriculum content
  (`README.md`, `project/INSTRUCTIONS.md`, `project/INTEGRATE.md`, `slides.pdf`,
  `examples/`) — no student artifacts exist yet.

---

## Step 1 — Scaffold working folder

Directly under `assisted-to-agentic-module-1/`, create:

- `prompts/` folder
- `JOURNAL.md` — using the template below (Prompt / Tool / Mode / Context / Model /
  Input / Output / Cost / Reflections), one entry per collaboration, filled in as you
  go, per this repo's own [AGENTS.md](../AGENTS.md) convention ("every meaningful AI
  collaboration gets a journal entry before moving on").
- `AGENTS.md` — empty skeleton to start, per the course's setup instructions ("touch
  AGENTS.md ... you'll build this out properly in Module 2"). This is a *different*
  file from the repo-root `AGENTS.md` — it's this module's project-root file, and
  Step 5 below is where code-convention entries get added to it.

`config-service/` is not created yet — it's populated in Step 5 once an
implementation plan exists.

`git init` is already done at the repo root — skip it.

## Step 2 — `prompts/1-web-api-specs.md`

Write the spec, covering all of the exercise's required areas, using the "Decisions
already made" section above as the content:

- Programming language (.NET 10 / C#, ASP.NET Core Web API, MVC controllers)
- Web framework and key dependencies (AWSSDK.DynamoDBv2, Serilog.AspNetCore,
  Microsoft.AspNetCore.OpenApi + Scalar.AspNetCore, xunit + Moq + coverlet,
  DotNetEnv)
- Architecture (Controller → Service → Repository, `Ignition/*.cs` DI registration,
  domain-grouped `Exceptions/`, `GlobalUsings.<Layer>.cs`)
- API endpoints and payload shapes (`/api/v1/applications`, `/api/v1/configurations`,
  CRUD)
- Database engine and driver (AWS DynamoDB, real account, on-demand billing, PITR
  off, region `ap-southeast-6` (New Zealand) — real/deployable, not file-based)
- AWS credentials via a local git-ignored `.env` file loaded by `DotNetEnv`
- Data access approach and migration strategy (repository-per-entity over
  `IDynamoDbCollection<T>`; versioned table-provisioning script instead of SQL
  migrations)
- API documentation and manual testing (Scalar UI over the OpenAPI document; service
  must be fully workable end-to-end, not just scaffolded)
- Testing approach and tooling (xunit + Moq, sibling `*.UnitTests` project)
- The "Looking ahead" Module 3 flags note, translated to the DynamoDB key design
  above

At the **top of this same file**, per Step 3b, add the prompt-creation preamble
instructions (adapt the example in INSTRUCTIONS.md §3b):

> This document contains details necessary to create a prompt, which will later be
> used to create an implementation plan for a REST Web API. Please review the
> contents of this file and recommend a PROMPT that can be sent to an AI coding
> assistant for help with creating an implementation plan for this service.
>
> The prompt should:
> - ask the assistant to create a comprehensive plan that includes dependencies,
>   file/folder structure, and architectural patterns.
> - recommend strict adherence to ALL of the details in this document.
> - strongly encourage the assistant to not add any additional dependencies without
>   approval.
> - encourage the assistant to ask for more information if they need it.

## Step 3 — Collaborate to create a prompt

a. New `JOURNAL.md` entry:
   - Prompt: `Read @/prompts/1-web-api-specs.md and follow the instructions at the top of the file.`
   - Tool: Claude Code
   - Mode: Plan
   - Context: Clean
   - Model: claude-sonnet-5
   - Input: `prompts/1-web-api-specs.md`
   - Output: `prompts/2-web-api-prompt.md`
   - Cost / Reflections: fill in after the run

b. Issue that prompt to Claude Code in a clean context, in Plan mode. Save the
   response to `prompts/2-web-api-prompt.md`.

c. Review the generated prompt, record cost and reflections in the journal entry.

d. Commit everything (`prompts/1-web-api-specs.md`, `prompts/2-web-api-prompt.md`,
   `JOURNAL.md`) before moving on. If you want to redo/iterate on this step first,
   commit before iterating.

## Step 4 — Collaborate to create a plan

a. New journal entry:
   - Prompt: `Read @/prompts/2-web-api-prompt.md and follow the instructions at the top of the file.`
   - Mode: Plan
   - Context: Clean
   - Input: `prompts/2-web-api-prompt.md`
   - Output: `prompts/3-web-api-plan.md`

b. Issue the prompt, save the response to `prompts/3-web-api-plan.md`.

c. Review the plan, record cost/reflections in the journal entry.

d. Commit before moving on (same discipline as Step 3d).

## Step 5 — Execute the implementation plan

a. New journal entry:
   - Prompt: `Please create a Config API Service in the config-service folder, according to the Implementation Plan defined in @/prompts/3-web-api-plan.md`
   - Mode: Act
   - Context: Clean
   - Model: claude-sonnet-5
   - Input: `prompts/3-web-api-plan.md`
   - Output: `config-service/`

b. Issue the prompt in Act mode (read+edit filesystem access). Monitor the
   scaffolding as it happens; interrupt if it goes off track.

c. Review the scaffolded project; capture reflections in the journal entry.

d. Capture any code-level conventions you want followed going forward in this
   module's `AGENTS.md` (the one created in Step 1, at
   `assisted-to-agentic-module-1/AGENTS.md`) — most AI coding tools auto-load this.

e. Ensure `config-service/.gitignore` is in place and correct (bin/obj folders,
   `.env`/user-secrets, etc.), then commit everything before moving on.

### AWS DynamoDB table provisioning (part of Step 5, before/alongside running the service)

This is real infrastructure creation in your AWS account — confirm table names and
region with you before creating anything, even though you've already authorized the
approach:

- Region: `ap-southeast-6` (Asia Pacific / New Zealand) — confirm or override
- Tables: `applications`, `configurations` (names may get a module/env prefix to
  avoid clashing with unrelated tables in the same account — confirm naming)
- Billing mode: `PAY_PER_REQUEST`
- Point-in-time recovery: disabled
- Key schema: `applications` — partition key `id`; `configurations` — partition key
  `applicationId`, sort key `configKey`
- State the resulting cost expectation (near-$0 at this usage level) before creating,
  per this session's standing instruction to state cost implications before
  provisioning cloud resources.

## Step 6 — Rinse & repeat (optional)

You can iterate from any earlier step without restarting — edit the spec/prompt/plan
and regenerate downstream assets. `examples/web-api-example-specs.md` is available as
an alternate spec to try (different stack — Python/FastAPI/Postgres) for comparison.
Commit each experiment separately so they stay comparable.

## Step 7 — Collaborative code improvements

Once the scaffolded project is accepted and unit tests pass, make the first
improvement *through* the assistant (brainstormer/mentor/QA roles) rather than by
hand-editing. Journal and commit frequently, same discipline as above.

## Step 8 — Compare against the reference example

The course provides a Python reference implementation at
`examples/config-service/svc` for comparison once your own service is working
end-to-end (different stack, same exercise) — read-only reference, don't copy from
it directly.

---

## Verification (end of exercise)

- `assisted-to-agentic-module-1/{prompts/,JOURNAL.md,AGENTS.md,config-service/}`
  all exist with real content, each exercise step's output committed separately per
  the "commit before iterating" discipline.
- `config-service/` builds and its unit test suite passes (`dotnet test`).
- The two DynamoDB tables exist in AWS (`ap-southeast-6`, New Zealand), on-demand
  billing, PITR disabled, and the running service can read/write through them
  end-to-end (exercise a create + list call against `/api/v1/applications`).
- `JOURNAL.md` has one complete entry (all 9 fields) per collaboration, in order.
- `INTEGRATE.md`'s 6 reflection prompts answered before moving to Module 2.

**Status: all of the above complete** — see `JOURNAL.md` for the full collaboration
record and `INTEGRATE-REFLECTIONS.md` for the answered reflection prompts.
