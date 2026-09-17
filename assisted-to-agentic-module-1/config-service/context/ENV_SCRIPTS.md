# Environments and Scripts

Procedural memory: how to run this project. Read this before running anything
by hand - if a command you need isn't listed here, that's a gap to fix in
this file, not a reason to guess.

## Environments

Local development only. No CI/CD, no staging, no production deployment
configured yet (see `context/IMPLEMENTATION.md`). Everything below assumes a
local machine with the API, database, and Admin UI all running on
`localhost`.

## Ports

| What | Port | Notes |
| --- | --- | --- |
| API (`src/ConfigApi.Service`) | `5038` | `dotnet run` dev default (see `Properties/launchSettings.json`) |
| Admin UI (`ui/`, Vite dev server) | `5173` | Vite default; the API's `LocalDev` CORS policy only allows this origin |

DynamoDB itself is not local - the API talks to real tables in AWS
`ap-southeast-6`. There is no local DynamoDB container in this project.

## Environment variables

Defined in `config-service/.env` (git-ignored; copy from `.env.example`):

| Variable | Purpose |
| --- | --- |
| `AWS_ACCESS_KEY_ID` | AWS credential for the IAM principal with DynamoDB access |
| `AWS_SECRET_ACCESS_KEY` | AWS credential, paired with the above |
| `AWS_REGION` | `ap-southeast-6` - must match where the `applications`/`configurations`/`flags` tables live |

Loaded via `DotNetEnv.Env.Load()` as the first line of `Program.cs`, then
picked up by the AWS SDK's standard credential chain. Never commit `.env`.

The Admin UI has one optional Vite env var, `VITE_API_BASE_URL`, defaulting
to `http://localhost:5038` when unset (see `ui/src/api.ts`). Only needs
setting if the API is running somewhere other than the default port.

Non-secret config (DynamoDB table names, scan cache TTL) lives in
`appsettings.json` under `DynamoDB`, not in `.env` - see
`context/IMPLEMENTATION.md`.

## Developer scripts

All commands run from the `config-service/` root unless noted. The root
`package.json` is the task runner for both the API (`src/`) and the UI
(`ui/`) - run `npm run` with no arguments to list everything it knows about.

### Setup

```bash
npm run install          # dotnet restore + npm install --prefix ui
cd ui && npm install      # (equivalent, ui only)
```

Copy `.env.example` to `.env` and fill in real AWS credentials before running
anything that touches DynamoDB.

### Provisioning (one-time / after a schema change)

```bash
npm run provision         # dotnet run --project infra/ConfigApi.Provisioning
```

Idempotent - creates `applications`/`configurations`/`flags` tables if they
don't exist, skips ones that do. See `infra/README.md` for the migration
numbering convention. Run this after adding a new migration, before running
the API against it.

### Running

```bash
npm run run:api           # dotnet run --project src/ConfigApi.Service (localhost:5038)
npm run run:ui             # vite dev server (localhost:5173) - needs run:api already up
```

### Testing

```bash
npm run test               # test:api + test:ui (unit suites only)
npm run test:api           # dotnet test src/ConfigApi.Service.sln
npm run test:ui             # vitest run (mocked unit suite, ui/src/api.test.ts)
npm run test:ui:integration # vitest against the real running API - start run:api first
```

Coverage (not wired into a script yet - run directly when needed):

```bash
dotnet test src/ConfigApi.Service.sln --settings src/ConfigApi.Service.UnitTests/coverlet.runsettings --collect:"XPlat Code Coverage"
```

**Windows gotcha**: stop any running `dotnet run` / `npm run run:api`
process before `dotnet test` or `dotnet build` - the rebuild step can't
overwrite a locked `.exe` and fails with `MSB3027`. Find and stop it with:

```bash
powershell -NoProfile -Command "Get-Process ConfigApi.Service -ErrorAction SilentlyContinue | Stop-Process -Force"
```

### Quality gates (required before a task is considered done, from Module 3 on)

```bash
npm run check               # test + lint + format:check + type-check, all of it
npm run lint                 # lint:api (dotnet build, warnings-as-errors) + lint:ui (eslint)
npm run format               # format:api (dotnet format, writes) + format:ui (prettier --write)
npm run format:check         # same as format, but verify-only (no writes) - what `check` uses
npm run type-check            # tsc -b (ui/ only; the API's type checking is the C# compiler itself, covered by lint:api)
```

`lint:api` doubles as the API's compiler-warning gate:
`TreatWarningsAsErrors` is on in `ConfigApi.Service.csproj`, so any warning
fails `dotnet build` directly. `format:api`/`lint:api` use `dotnet format`,
which ships with the .NET SDK - no extra dependency. `lint:ui`/`format:ui`
use ESLint (flat config, `ui/eslint.config.js`) and Prettier
(`ui/.prettierrc.json`), both dev-only dependencies in `ui/package.json`.

All of `test`, `lint`, `format:check`, and `type-check` must pass with zero
warnings and zero skipped tests before a BUILD & ASSESS stage is done - see
`context/WORKFLOW_STATUS.md`.

### Building

```bash
npm run build:ui            # tsc -b && vite build -> ui/dist/
```

No build step for the API in local dev (`dotnet run` compiles and runs
directly).

### Dependency audits

Run after any `npm install` / version bump in `ui/` - this isn't
hypothetical, a past `npm install` there pulled in known CVEs transitively
(see `context/IMPLEMENTATION.md`):

```bash
npm audit --prefix ui
```

## When to go off-script

Direct `dotnet`/`npm` commands (bypassing the `npm run ...` wrappers above)
are fine for:

- One-off troubleshooting or debugging a single component (e.g. running one
  test class, inspecting a specific `dotnet format` diagnostic)
- Investigating something this file doesn't yet cover

They are not fine as a substitute for the documented scripts during normal
development, testing, or the BUILD & ASSESS quality gate - use the `npm run
...` commands above so everyone (and every assistant session) runs the same
checks the same way. If you find yourself reaching for a direct command
repeatedly, that's a signal this file is missing something - add it here
instead of leaving it as tribal knowledge.
