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

# Configuration API Service — Specification

## Programming language

C#, .NET 10, ASP.NET Core Web API (`Microsoft.NET.Sdk.Web`). Use MVC controllers,
not Minimal APIs.

## Web framework and key dependencies

- `AWSSDK.DynamoDBv2` — DynamoDB data access
- `Serilog.AspNetCore` — logging
- `Microsoft.AspNetCore.OpenApi` + `Scalar.AspNetCore` — API docs/UI
- `xunit`, `Moq`, `coverlet.collector`/`coverlet.msbuild` — testing and coverage
- `DotNetEnv` — loads AWS credentials from a local `.env` file at startup

Do not add any dependency beyond this list without approval.

Project settings: `Nullable` and `ImplicitUsings` enabled, `TreatWarningsAsErrors`.

## Architecture

Controller → Service → Repository, patterned after the reference project
`income-service` (github.com/burger-mtbkr/income-service):

- One `IDynamoDbCollection<T>`-style repository per entity.
- DI registration grouped into `Ignition/*.cs` static classes (e.g.
  `DynamoDbIgnition`, `ServicesIgnition`, `RepositoryIgnition`).
- Domain-grouped `Exceptions/` folder.
- `GlobalUsings.<Layer>.cs` per layer (e.g. `GlobalUsings.Controllers.cs`,
  `GlobalUsings.Services.cs`, `GlobalUsings.Repositories.cs`).

## API endpoints and payload shapes

REST CRUD under `/api/v1`, for two resources:

- `/api/v1/applications`
  - `GET /api/v1/applications` — list applications
  - `GET /api/v1/applications/{id}` — get one application
  - `POST /api/v1/applications` — create an application
  - `PUT /api/v1/applications/{id}` — update an application
  - `DELETE /api/v1/applications/{id}` — delete an application
- `/api/v1/configurations`
  - `GET /api/v1/applications/{applicationId}/configurations` — list configurations
    for an application
  - `GET /api/v1/applications/{applicationId}/configurations/{configKey}` — get one
    configuration entry
  - `POST /api/v1/applications/{applicationId}/configurations` — create a
    configuration entry
  - `PUT /api/v1/applications/{applicationId}/configurations/{configKey}` — update a
    configuration entry
  - `DELETE /api/v1/applications/{applicationId}/configurations/{configKey}` —
    delete a configuration entry

Exact request/response DTO shapes are left to the implementation plan, but every
configuration entry belongs to exactly one application (`applicationId` is a
required foreign-key-equivalent reference).

Also expose a health check endpoint: `GET /health` — returns 200 with a small
status payload when the service is up, used to verify the deployed service is
reachable.

`Application.Name` uniqueness is enforced: `POST /api/v1/applications` with a
name that already exists returns `409 Conflict`.

A static OpenAPI spec file (generated from the service's own OpenAPI document)
is committed at the service root (`config-service/openapi.json`), alongside the
live Scalar UI, so the API surface is reviewable without running the service.

## Database engine and driver

AWS DynamoDB, a real AWS account — not DynamoDB Local, not in-memory, not
file-based. This satisfies the requirement that the API be deployable.

- Two tables, one per entity (matching `income-service`'s pattern, not a
  single-table design):
  - `applications` — partition key `id`
  - `configurations` — partition key `applicationId`, sort key `configKey` (the
    DynamoDB equivalent of a relational foreign key to `applications`)
- Billing mode: on-demand (`PAY_PER_REQUEST`) — zero baseline cost, pay only for
  actual requests.
- Point-in-time recovery: disabled — no backups, minimal cost.
- Region: `ap-southeast-6` (Asia Pacific / New Zealand) unless stated otherwise.

### AWS credentials

AWS connectivity credentials (access key ID, secret access key, region) are supplied
via a local `.env` file at the repo root — never committed (must be listed in
`.gitignore`). Loaded into process environment variables at startup via `DotNetEnv`,
then picked up by the standard AWS SDK credential chain. Commit a `.env.example`
with the required variable names and no real values, for onboarding.

## Data access approach and migration strategy

No ORM, no SQL-style migrations (NoSQL). Repository-per-entity over an
`IDynamoDbCollection<T>`-style abstraction, matching `income-service`. Table and
key-schema definitions live in the repo as a small versioned provisioning script
(e.g. under `infra/`) that creates/updates the DynamoDB tables — the DynamoDB
analogue of a numbered SQL migrations folder.

## API documentation and manual testing

The service must be fully workable end-to-end against the real DynamoDB tables —
not just scaffolded. Use `Scalar.AspNetCore` (as a Swagger UI replacement) served
from `Microsoft.AspNetCore.OpenApi`'s generated OpenAPI document, enabled in the
dev environment, as the way to manually exercise every endpoint (CRUD for both
`applications` and `configurations`) without a separate client.

## Testing approach and tooling

`xunit` + `Moq`, tests colocated in a sibling `*.UnitTests` project mirroring the
source tree (`Controllers/`, `Services/`, `Repositories/`). Use `coverlet` for
coverage collection.

## Looking ahead

In Module 3 this service will be extended to support per-application feature
flags. A `flags` table keyed by `applicationId` (partition key) + `flagKey` (sort
key) is the DynamoDB-native equivalent of "a `flags` table with a foreign key to
`applications`" — worth keeping in mind when finalizing the key-schema decisions
above so the `configurations` and future `flags` tables stay consistent in shape.
