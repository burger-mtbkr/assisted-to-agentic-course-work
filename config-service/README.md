# Configuration API Service

A REST API for managing `applications` and their per-application
`configurations` and `flags`, backed by AWS DynamoDB. C#, .NET 10,
ASP.NET Core MVC controllers, Controller -> Service -> Repository
architecture (patterned after `income-service`).

## Prerequisites

- .NET 10 SDK
- An AWS account with access to DynamoDB in `ap-southeast-6` (Asia Pacific /
  New Zealand), and an IAM principal with permissions to describe/create/read/
  write the `applications`, `configurations`, and `flags` tables.

## 1. Configure AWS credentials

Copy `.env.example` to `.env` at the repo root (`config-service/.env`) and
fill in real values. `.env` is gitignored and must never be committed:

```
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-southeast-6
```

These are loaded into process environment variables at startup via
`DotNetEnv`, then picked up by the standard AWS SDK credential chain.

## 2. Provision the DynamoDB tables

Creates the `applications`, `configurations`, and `flags` tables if they
don't already exist (idempotent - safe to re-run):

```
dotnet run --project infra/ConfigApi.Provisioning
```

See `infra/README.md` for the migration numbering convention.

## 3. Run the API

```
dotnet run --project src/ConfigApi.Service
```

In the `Development` environment, the root path (`/`) redirects to the Scalar
UI, so opening `http://localhost:5038/` after `dotnet run` lands you straight
on it. The OpenAPI document and Scalar UI are also available directly, for
exercising every endpoint by hand:

- OpenAPI document (live): `/openapi/v1.json`
- OpenAPI document (static export, committed at the repo root for review
  without running the service): `openapi.json`
- Scalar UI: `/scalar`

Health check (no DynamoDB dependency): `GET /health`

## API endpoints

REST CRUD under `/api/v1`:

- `/api/v1/applications` - `GET`, `GET /{id}`, `POST`, `PUT /{id}`, `DELETE /{id}`
- `/api/v1/applications/{applicationId}/configurations` - `GET`, `GET /{configKey}`,
  `POST`, `PUT /{configKey}`, `DELETE /{configKey}`
- `/api/v1/applications/{applicationId}/flags` - `GET`, `GET /{flagKey}`,
  `POST`, `PUT /{flagKey}`, `DELETE /{flagKey}` (Module 3)

## Consuming feature flags safely

A flag can be in one of three states from a consuming application's point of
view, and they mean different things:

1. **`GET /{flagKey}` returns `200` with `"enabled": true`** - explicitly on.
2. **`GET /{flagKey}` returns `200` with `"enabled": false`** - explicitly
   off. Not the same as missing - someone deliberately disabled it.
3. **`GET /{flagKey}` returns `404`** - the flag was never created for this
   application. This is not "disabled" - it's "not configured yet," and
   should resolve to whatever default the *consuming* application chooses,
   not to `false` by convention.

Collapsing 404 and `enabled: false` into the same outcome is the most common
mistake: it silently turns "nobody has decided yet" into "explicitly turned
off," which is wrong whenever a flag's sane default is *on* (e.g. a flag
that guards a deprecated code path you're phasing out - missing should mean
"keep the new behavior," not "fall back to the old one").

A safe read pattern (C#, no SDK required - this API has no client library,
just plain HTTP):

```csharp
async Task<bool> IsEnabledAsync(HttpClient client, string applicationId, string flagKey, bool defaultValue)
{
    var response = await client.GetAsync($"/api/v1/applications/{applicationId}/flags/{flagKey}");

    if (response.StatusCode == HttpStatusCode.NotFound)
    {
        return defaultValue; // not configured yet - caller's default, not false
    }

    response.EnsureSuccessStatusCode();
    var flag = await response.Content.ReadFromJsonAsync<FlagResponse>();
    return flag!.Enabled; // explicit value from the service - trust it
}
```

Two more things worth knowing before wiring this into a hot path:

- **No caching or push updates.** Every call is a live read (scan-and-cache
  server-side, see `context/ARCHITECTURE.md`, but no client-side caching
  contract). A consuming application calling this per-request should add its
  own short-lived cache; this API doesn't do it for you.
- **Deleting an application requires removing its flags first** (`DELETE
  /applications/{id}` returns `409` while configuration entries or feature
  flags still exist) - if you're decommissioning a flag's owning
  application, clean up flags (and configurations) before the application
  itself.

## 4. Run the Admin UI

With the API running (step 3), in a separate terminal:

```
npm install --prefix ui
npm run dev --prefix ui
```

Opens on `http://localhost:5173`. The API's CORS policy only allows that
origin in `Development` - see `context/ARCHITECTURE.md`.

## Tests and coverage

From the repo root:

```
dotnet test src/ConfigApi.Service.sln
```

With coverage (uses `src/ConfigApi.Service.UnitTests/coverlet.runsettings`,
which excludes the `Infrastructure/DynamoDb` layer and `Ignition/DynamoDbIgnition`
since those touch the real AWS SDK client):

```
dotnet test src/ConfigApi.Service.sln --settings src/ConfigApi.Service.UnitTests/coverlet.runsettings --collect:"XPlat Code Coverage"
```

On Windows, stop any running `dotnet run`/`npm run run:api` instance first -
`dotnet test`'s rebuild step can't overwrite a `.exe` that's still locked by
a running process, and fails with an `MSB3027` copy error if one is.

## Quality gates

```
npm run check    # test + lint + format:check + type-check (api and ui)
```

Runs the API's build (warnings-as-errors) and `dotnet format`, the UI's
ESLint and Prettier, and the UI's TypeScript checking. See
`context/ENV_SCRIPTS.md` for the individual `lint`/`format`/`type-check`
scripts and what each one covers.

## Project layout

```
config-service/
├── .env.example
├── global.json
├── openapi.json                     # static export of the live OpenAPI document
├── package.json                     # task runner - run `npm run` for the full list
├── AGENTS.md                        # auto-loaded context framework pointer
├── context/                         # ABOUT.md, ARCHITECTURE.md, IMPLEMENTATION.md,
│                                     # ENV_SCRIPTS.md, WORKFLOW_STATUS.md
├── changes/                         # work items (template.md + NNN-name.md), see
│                                     # context/WORKFLOW_STATUS.md
├── infra/
│   └── ConfigApi.Provisioning/     # DynamoDB table provisioning (see infra/README.md)
├── src/
│   ├── ConfigApi.Service.sln
│   ├── ConfigApi.Service/          # the API (Controllers -> Services -> Repositories)
│   └── ConfigApi.Service.UnitTests/
└── ui/                              # Admin UI (TypeScript + Vite, no framework)
```
