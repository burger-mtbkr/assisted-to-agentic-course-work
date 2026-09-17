# Module 1 conventions (config-service)

Captured while building `config-service/` in Step 5 — apply these going forward
for this module.

- **AWSSDK.DynamoDBv2 `TableBuilder` needs explicit key definitions.**
  `new TableBuilder(client, tableName).Build()` throws `ArgumentOutOfRangeException:
  A hash key definition is required, call AddHashKey before Build.` at runtime —
  it doesn't infer the schema. Always call `.AddHashKey(name, DynamoDBEntryType.String)`
  (and `.AddRangeKey(...)` for composite keys) before `.Build()`. `Table.LoadTable(client,
  tableName)` looks like the fix but is marked `[Obsolete]` in this SDK version, which
  fails the build under `TreatWarningsAsErrors`.
- **Only build what the current spec/prompt/plan asks for.** An earlier draft of
  `prompts/3-web-api-plan.md` added request DTOs and an `UpdatedDate` field the spec
  never asked for; both were cut on review. Don't reintroduce speculative fields,
  DTOs, or abstractions without them being asked for first.
- **`.env` (AWS credentials) is local-dev-only and never committed** — `config-service/.gitignore`
  covers it. Use a scoped least-privilege IAM user for local DynamoDB access (this
  project has `config-service-local-dev`, limited to the `applications`/`configurations`
  tables), never the AWS account root credentials.
- **`openapi.json`** at the `config-service/` root is a static export of the live
  `/openapi/v1.json` document, committed for review without running the service.
  Regenerate it (`curl http://localhost:5038/openapi/v1.json -o openapi.json` while
  the service is running) after any change to controller routes or DTO shapes.
- **Root path (`/`) redirects to Scalar (`/scalar`) in Development** — `dotnet run`
  should always land you on the interactive API UI, not a 404.
