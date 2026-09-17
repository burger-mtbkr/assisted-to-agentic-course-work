# Architecture

## Layers

Controller -> Service -> Repository, wired up in `Program.cs` via
`Ignition/*.cs` static extension classes (`ConfigureLogging`,
`ConfigureDynamoDb`, `ConfigureRepositories`, `ConfigureServices`, in that
order):

- **Controllers** (`Controllers/Applications`, `Controllers/Configurations`,
  `Controllers/Health`) - MVC controllers, HTTP concerns only (routing,
  status codes). Translate service results (`null` = not found, `bool` /
  `bool?` for conditional outcomes) into `IActionResult`.
- **Services** (`Services/Applications/ApplicationService`,
  `Services/Configurations/ConfigurationService`) - business rules: name
  uniqueness, id/timestamp generation, the delete-with-children guard.
  Throw domain exceptions for the caller-facing failure cases.
- **Repositories** (`Repositories/Applications/ApplicationRepository`,
  `Repositories/Configurations/ConfigurationRepository`) - thin wrappers
  around the DynamoDB collection abstractions (below); no business logic.

## Data access

Two collection abstractions in `Infrastructure/DynamoDb/`, both ported from
`income-service` and both scan-all-then-filter (no query-by-index yet) with
a TTL-cached, invalidate-on-write scan (`DynamoDbTableCache`):

- `IDynamoDbCollection<T>` / `DynamoDbCollection<T>` - single partition key
  (`"id"`). Used for `applications`.
- `IDynamoDbCompositeKeyCollection<T>` / `DynamoDbCompositeKeyCollection<T>`
  - partition key + sort key. Added because `income-service`'s original
  collection type is hard-wired to a single `"id"` key and can't express
  `configurations`' `(applicationId, configKey)` schema. Used for
  `configurations` (partition `applicationId`, sort `configKey`).

Both wrap AWS SDK's `TableBuilder`, which requires the key schema declared
explicitly via `.AddHashKey(...)` (and `.AddRangeKey(...)` for the composite
variant) before `.Build()` - it does not infer schema from the table. This
was the source of a real outage during Module 1 (see
`context/IMPLEMENTATION.md`'s Testing section): unit tests mock these
interfaces, so a missing `AddHashKey` call passed all 55 tests but threw
`ArgumentOutOfRangeException` on the very first live request.

## Error handling

Two different paths produce two different JSON shapes for what are
conceptually similar errors - worth knowing when integrating a client:

- **Thrown domain exceptions** (`ApplicationNotFoundException`,
  `ConfigurationNotFoundException`, `DuplicateApplicationNameException`,
  `DuplicateConfigurationKeyException`, `ValidationException`) are caught
  centrally by `Middleware/ErrorMiddleware`, mapped to 404/404/409/409/400,
  and serialized as `{ status, title, detail, error, exceptionType,
  traceId }`.
- **`ApplicationsController.Delete`** returns a tri-state result from
  `ApplicationService.DeleteAsync` (`bool?`: `null` = not found, `false` =
  conflict because the application still has configuration entries, `true`
  = deleted) directly as `NotFound()` / `Conflict()` / `NoContent()` -
  bypassing `ErrorMiddleware`, so that specific 409 comes back as ASP.NET's
  default `ProblemDetails` shape (`{ type, title, status, traceId }`)
  instead.

Unhandled exceptions fall through to a generic 500 in `ErrorMiddleware`.

## API surface

REST CRUD under `/api/v1` for `applications` and nested
`applications/{applicationId}/configurations`, plus a dependency-free
`GET /health`. Full contract: the committed `openapi.json`, the live
`/openapi/v1.json`, or the Scalar UI at `/scalar` (dev only) - see
`config-service/README.md` rather than duplicating the endpoint list here.

## Key technical decisions

- **Separate tables, not single-table design** - `applications`,
  `configurations`, and (Module 3) `flags` are separate DynamoDB tables
  (matching `income-service`'s pattern), not modeled as one table with
  composite sort keys. `flags` mirrors `configurations`' composite-key
  shape (`applicationId` partition, `flagKey` sort).
- **Scan-and-cache reads, not indexed queries** - both collection types read
  via a full table scan, cached for `ScanCacheSeconds` (see
  `appsettings.json`'s `DynamoDB` section) and invalidated on every write.
  Fine at current scale; would need a GSI/query-based approach if
  `configurations` grows large per application.
- **CORS** - `Ignition/CorsIgnition.cs` registers a `LocalDev` policy scoped
  to `http://localhost:5173` (the Admin UI's Vite dev server), applied via
  `app.UseCors(...)` only when `IsDevelopment()` - same gating as
  Scalar/OpenAPI. No CORS policy exists outside Development.
- **No authentication/authorization** - see `context/ABOUT.md` Scope.

## UI

`ui/` (sibling to `src/`) - TypeScript + Vite, no framework; see
`context/IMPLEMENTATION.md` for why. Two files carry all the logic:

- `src/api.ts` - a thin `fetch` wrapper (`listApplications`,
  `listConfigurations`, `updateConfiguration`) that talks to the API at
  `VITE_API_BASE_URL` (defaults to `http://localhost:5038`) and normalizes
  both error-response shapes documented above into a single `Error` with a
  human-readable message.
- `src/main.ts` - direct DOM rendering, no virtual DOM/templating: an
  applications list panel and a configurations panel, toggled via
  `hidden`. No client-side router - this is a two-screen tool, not an SPA
  that needs one.

Data flow: `main.ts` calls `api.ts`, which calls the real API directly from
the browser (no server-side proxy) - this is what the CORS policy above
exists for.
