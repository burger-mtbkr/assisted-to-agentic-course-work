# Implementation

## Technology stack

**Service** (`src/ConfigApi.Service`): C#, .NET 10 (`net10.0`), ASP.NET Core
Web API with MVC controllers (not Minimal APIs). `Nullable` and
`ImplicitUsings` enabled, `TreatWarningsAsErrors` on. Dependencies (do not
add more without a reason - this list is deliberately short):

- `AWSSDK.DynamoDBv2` 4.0.103.5 - DynamoDB data access
- `DotNetEnv` 3.2.0 - loads `.env` into process environment at startup
- `Microsoft.AspNetCore.OpenApi` 10.0.11 + `Scalar.AspNetCore` 2.17.2 - live
  OpenAPI document and API explorer UI
- `Serilog.AspNetCore` 10.0.0 - structured request logging

**Tests** (`src/ConfigApi.Service.UnitTests`): xunit + Moq, `coverlet` for
coverage.

## Configuration and credentials

AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
`AWS_REGION`) come from a git-ignored `.env` at the `config-service` root,
loaded via `DotNetEnv.Env.Load()` as the very first line of `Program.cs`,
then picked up by the AWS SDK's standard credential chain. `.env.example`
is committed with empty values for onboarding. Non-secret config
(DynamoDB table names, scan cache TTL) lives in `appsettings.json` under a
`DynamoDB` section, bound to `DynamoDbSettings`.

## Validation

There is currently no field-level validation on `Application` or
`Configuration` (no `[Required]`, length limits, or key-format
constraints) - any string, including empty, is accepted for `name`,
`value`, etc. The only enforced business rules are uniqueness
(`Application.Name`, `Configuration.ConfigKey` within an application) and
existence checks (404 on operations against a missing parent/entity). Keep
this in mind when building the Admin UI: the API won't reject malformed
input, so basic UX-level guards (e.g. not submitting an empty key) belong
in the UI itself.

## Testing

Tests are colocated in a sibling `*.UnitTests` project, mirroring the
source tree one-to-one (`Controllers/`, `Services/`, `Repositories/`,
`Middleware/`, `Ignition/`). Repositories mock the DynamoDB collection
interfaces; services mock repositories; controllers mock services -
nothing in the unit suite touches a real AWS client. Coverage via
`coverlet`, using `src/ConfigApi.Service.UnitTests/coverlet.runsettings`,
which excludes `Infrastructure/DynamoDb` and `Ignition/DynamoDbIgnition`
(the parts that construct a real `TableBuilder`) - those are only verified
by running the service against real DynamoDB. This is a deliberate gap,
not an oversight: it's exactly the boundary that hid the `TableBuilder`
bug during Module 1, so treat "tests pass" as necessary but not
sufficient - a live run against the real API (see `config-service/README.md`)
is still the final check after any change to that layer.

## Admin UI stack (this module)

**TypeScript + Vite + Vitest, no UI framework**, calling the API directly
with `fetch`. Chosen because: the UI's scope is three small views (list
apps, view one app's config entries, edit a value) - a framework like
React would add a dependency and a build-concept for no real benefit at
this size; Vite/Vitest gives a fast dev server and a real test setup
without hand-rolling either; and it mirrors the course's own reference
implementation's approach (see
`assisted-to-agentic-module-2/examples/config-service/ui/`), which the
Module 2 instructions hold up as the shape of a "resist scope creep" admin
tool. `ui/` sits as a sibling to `src/`, with its own `package.json` (see
`config-service/package.json` for the cross-project task runner that
drives both `svc` and `ui`).

API base URL is `VITE_API_BASE_URL` (Vite env var), defaulting to
`http://localhost:5038` - the service's dev port - when unset. `npm test`
runs only the mocked unit suite (`src/api.test.ts`); `npm run test:integration`
runs `src/integration/api.test.ts`, which exercises the same `api.ts`
functions against the real running service (create/list/update/read-back,
cleaning up after itself) - this is deliberately not part of the default
`npm test` run since it needs the service up. Run it after any change to
`api.ts` or to the service's request/response contract, same principle as
the "tests pass isn't enough" note above.

`tsconfig.json` sets `noEmit: true` - `tsc -b` in the `build` script is
type-checking only; Vite does the actual bundling. Omitting `noEmit` makes
`tsc` emit `.js` files alongside the `.ts` sources in `src/`, which Vitest
then picks up as duplicate test files - hit this once during Module 2 and
fixed it.

## Development workflow

Plan-then-act per change, one commit per meaningful step, plain descriptive
commit messages (`"Module N: <what changed>"`, not a conventional-commits
format) - observed directly from `git log`, not an invented policy. No
CI/CD configured yet.
