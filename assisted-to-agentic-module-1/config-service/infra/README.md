# infra/

DynamoDB table provisioning for the Configuration API Service. This is the
DynamoDB analogue of a numbered SQL migrations folder: no ORM, no SQL, just a
small ordered list of idempotent table-creation steps.

## Numbering convention

- Migration files live in `ConfigApi.Provisioning/Migrations/`, named
  `NNNN_Description.cs` with a four-digit, strictly increasing prefix
  (`0001_CreateApplicationsTable.cs`, `0002_CreateConfigurationsTable.cs`,
  `0003_CreateFlagsTable.cs`).
- Once a migration is merged, its number and behavior are never edited.
  Schema changes are new migrations with the next number.
- `0003` creates the `flags` table (Module 3: `applicationId` partition key
  + `flagKey` sort key, matching the `configurations` table's shape).

## How to run

From the repo root (`config-service/`), with a populated `.env` at the repo
root (see `.env.example`):

```
dotnet run --project infra/ConfigApi.Provisioning
```

This loads `.env` via `DotNetEnv.Env.Load()`, then runs every migration in
`Migrations/` in ascending `Version` order against the real AWS account.

## Idempotency

Each migration calls `DescribeTable` first. If the table already exists, it
logs "already exists, skipping" and does nothing further. If DynamoDB returns
`ResourceNotFoundException`, the migration creates the table. Running the
provisioning project repeatedly against tables that already exist is safe and
makes no changes.
