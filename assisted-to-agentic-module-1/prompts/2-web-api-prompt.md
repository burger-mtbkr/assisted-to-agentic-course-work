You are an expert .NET backend architect. I need a comprehensive, step-by-step implementation plan for a REST Web API called the **Configuration API Service**. Do not write the implementation itself yet — only produce the plan. Ask me clarifying questions first if anything below is ambiguous or if you need more information before you can plan confidently; do not guess or assume when a detail is missing.

Follow every detail in this specification exactly and strictly. Do not deviate from it, and do not add any NuGet package, library, or other dependency beyond the ones explicitly listed below without asking for my approval first.

## Programming language and runtime

C#, .NET 10, ASP.NET Core Web API (`Microsoft.NET.Sdk.Web`). Use MVC controllers — do not use Minimal APIs.

## Approved dependencies (do not add anything beyond this list without approval)

- `AWSSDK.DynamoDBv2` — DynamoDB data access
- `Serilog.AspNetCore` — logging
- `Microsoft.AspNetCore.OpenApi` + `Scalar.AspNetCore` — API docs/UI
- `xunit`, `Moq`, `coverlet.collector`/`coverlet.msbuild` — testing and coverage
- `DotNetEnv` — loads AWS credentials from a local `.env` file at startup

Project settings must enable `Nullable` and `ImplicitUsings`, and set `TreatWarningsAsErrors`.

## Architecture

Controller → Service → Repository pattern, modeled directly on the reference project `income-service` (github.com/burger-mtbkr/income-service). Specifically:

- One `IDynamoDbCollection<T>`-style repository per entity.
- DI registrations grouped into `Ignition/*.cs` static classes (e.g. `DynamoDbIgnition`, `ServicesIgnition`, `RepositoryIgnition`).
- A domain-grouped `Exceptions/` folder.
- Per-layer `GlobalUsings.<Layer>.cs` files (e.g. `GlobalUsings.Controllers.cs`, `GlobalUsings.Services.cs`, `GlobalUsings.Repositories.cs`).

If you are not already familiar with the structure and conventions of `income-service`, ask me for more detail about it rather than guessing.

## API endpoints and payload shapes

Implement REST CRUD under `/api/v1` for two resources:

**Applications** (`/api/v1/applications`)
- `GET /api/v1/applications` — list applications
- `GET /api/v1/applications/{id}` — get one application
- `POST /api/v1/applications` — create an application
- `PUT /api/v1/applications/{id}` — update an application
- `DELETE /api/v1/applications/{id}` — delete an application

**Configurations** (nested under an application)
- `GET /api/v1/applications/{applicationId}/configurations` — list configurations for an application
- `GET /api/v1/applications/{applicationId}/configurations/{configKey}` — get one configuration entry
- `POST /api/v1/applications/{applicationId}/configurations` — create a configuration entry
- `PUT /api/v1/applications/{applicationId}/configurations/{configKey}` — update a configuration entry
- `DELETE /api/v1/applications/{applicationId}/configurations/{configKey}` — delete a configuration entry

Exact request/response DTO shapes are not prescribed — propose them as part of the plan. Every configuration entry must belong to exactly one application, with `applicationId` as a required foreign-key-equivalent reference.

## Database engine and driver

AWS DynamoDB, using a real AWS account — not DynamoDB Local, not in-memory, not file-based — so the API remains genuinely deployable.

- Two separate tables (one per entity, matching `income-service`'s pattern — not a single-table design):
  - `applications` — partition key `id`
  - `configurations` — partition key `applicationId`, sort key `configKey` (the DynamoDB equivalent of a relational foreign key to `applications`)
- Billing mode: on-demand (`PAY_PER_REQUEST`).
- Point-in-time recovery: disabled.
- Region: `ap-southeast-6` (Asia Pacific / New Zealand) unless I state otherwise.

### AWS credentials

AWS connectivity credentials (access key ID, secret access key, region) are supplied via a local `.env` file at the repo root — never committed (must be listed in `.gitignore`). Loaded into process environment variables at startup via `DotNetEnv`, then picked up by the standard AWS SDK credential chain. Commit a `.env.example` with the required variable names and no real values, for onboarding.

## Data access approach and migration strategy

No ORM and no SQL-style migrations (this is NoSQL). Use a repository-per-entity approach over an `IDynamoDbCollection<T>`-style abstraction, matching `income-service`. Table and key-schema definitions must live in the repo as a small, versioned provisioning script (e.g. under `infra/`) that creates/updates the DynamoDB tables — this is the DynamoDB analogue of a numbered SQL migrations folder.

## API documentation and manual testing

The service must be fully workable end-to-end against the real DynamoDB tables — not just scaffolded. Use `Scalar.AspNetCore` (as a Swagger UI replacement) served from `Microsoft.AspNetCore.OpenApi`'s generated OpenAPI document, enabled in the dev environment, as the way to manually exercise every endpoint (CRUD for both `applications` and `configurations`) without a separate client.

## Testing approach and tooling

Use `xunit` + `Moq`, with tests colocated in a sibling `*.UnitTests` project that mirrors the source tree (`Controllers/`, `Services/`, `Repositories/`). Use `coverlet` for coverage collection.

## Forward-looking constraint

In a later phase, this service will be extended to support per-application feature flags via a `flags` table keyed by `applicationId` (partition key) + `flagKey` (sort key) — the DynamoDB-native equivalent of "a `flags` table with a foreign key to `applications`." When finalizing key-schema decisions for the `configurations` table, keep this future `flags` table in mind so the two stay consistent in shape and convention.

## What I need from you

Produce a comprehensive implementation plan that includes, at minimum:

1. Full file/folder structure for both the main API project and the `*.UnitTests` project, consistent with the `income-service` architectural pattern described above.
2. The architectural approach for each layer (Controller, Service, Repository, Ignition, Exceptions, GlobalUsings) and how they interact.
3. Proposed DTO/model shapes for `Application` and `Configuration` entities, and how they map to the DynamoDB table schemas described above.
4. The DynamoDB provisioning script approach under `infra/` (what it creates, how it's versioned, how it's run).
5. Dependency injection setup across the `Ignition/*.cs` classes.
6. Error handling/exception strategy (tied to the `Exceptions/` folder).
7. Testing strategy and structure for the `*.UnitTests` project, including how repositories will be mocked with `Moq`.
8. API documentation setup via `Microsoft.AspNetCore.OpenApi` + `Scalar.AspNetCore`.
9. Logging setup via `Serilog.AspNetCore`.
10. Sequencing/ordering of implementation steps and any dependencies between them.
11. Any open questions, ambiguities, or missing information you need me to resolve before or during implementation — ask these explicitly rather than assuming.

Adhere strictly to every detail in this specification. If anything is unclear or you need more context (including about the `income-service` reference project) to produce an accurate plan, ask me before proceeding.
