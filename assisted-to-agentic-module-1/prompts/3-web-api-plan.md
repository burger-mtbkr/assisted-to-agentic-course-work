# Configuration API Service — Implementation Plan

Grounded in the actual structure of `github.com/burger-mtbkr/income-service` (fetched directly from GitHub: `Program.cs`, `Ignition/*.cs`, `Infrastructure/DynamoDb/*.cs`, a representative `Repositories/Contacts`, `Controllers/Contacts`, `Exceptions/Income`, `Middleware/ErrorMiddleware.cs`, `GlobalUsings.*.cs`, both `.csproj` files, `coverlet.runsettings`, and `docs/dynamodb.md`). Two things in the spec have **no direct precedent** in that reference repo, so I made an explicit, clearly-labeled design decision for each rather than guessing silently — see the callouts in §2 and §4, and the consolidated list in §11.

Target location for the scaffolded project (per `project/INSTRUCTIONS.md` step 5): `assisted-to-agentic-module-1/config-service/`. Project/namespace name: `ConfigApi.Service` (mirrors `Income.Service`'s one-word-plus-`.Service` convention).

---

## 1. Full file/folder structure

```
config-service/
├── .gitignore                              # adds .env, bin/, obj/ (income-service's own .gitignore has no .env entry — it doesn't use DotNetEnv)
├── .env.example                             # AWS_ACCESS_KEY_ID=, AWS_SECRET_ACCESS_KEY=, AWS_REGION=ap-southeast-6
├── .env                                     # gitignored, real values, local only
├── global.json                              # { "sdk": { "version": "10.0.100", "rollForward": "latestFeature" } } — copied verbatim from income-service
├── openapi.json                             # static export of the live OpenAPI document, committed for review without running the service
├── README.md                                # setup, .env, provisioning, run, Scalar UI, test/coverage commands
├── infra/
│   ├── README.md                            # numbering convention, how to run, idempotency note
│   └── ConfigApi.Provisioning/
│       ├── ConfigApi.Provisioning.csproj     # net10.0 console; AWSSDK.DynamoDBv2 + DotNetEnv only (both already approved)
│       ├── Program.cs                        # loads .env, runs migrations in order, idempotent
│       └── Migrations/
│           ├── ITableMigration.cs
│           ├── 0001_CreateApplicationsTable.cs
│           └── 0002_CreateConfigurationsTable.cs
│           # 0003 reserved for the future `flags` table (Module 3) — documented in infra/README.md, not implemented here
└── src/
    ├── ConfigApi.Service.sln                 # 3 projects: Service, UnitTests, Provisioning (added for `dotnet build`/`dotnet test` from one root)
    ├── ConfigApi.Service/
    │   ├── ConfigApi.Service.csproj
    │   ├── Program.cs
    │   ├── appsettings.json
    │   ├── appsettings.Development.json
    │   ├── GlobalUsings.Controllers.cs
    │   ├── GlobalUsings.Services.cs
    │   ├── GlobalUsings.Repositories.cs
    │   ├── GlobalUsings.Models.cs
    │   ├── GlobalUsings.Exceptions.cs
    │   ├── GlobalUsings.Infrastructure.cs
    │   ├── Controllers/
    │   │   ├── Health/
    │   │   │   └── HealthController.cs        # GET /health — 200 + status payload, no dependencies
    │   │   ├── Applications/
    │   │   │   └── ApplicationsController.cs
    │   │   └── Configurations/
    │   │       └── ConfigurationsController.cs
    │   ├── Services/
    │   │   ├── Applications/
    │   │   │   ├── IApplicationService.cs
    │   │   │   └── ApplicationService.cs
    │   │   └── Configurations/
    │   │       ├── IConfigurationService.cs
    │   │       └── ConfigurationService.cs
    │   ├── Repositories/
    │   │   ├── Applications/
    │   │   │   ├── IApplicationRepository.cs
    │   │   │   └── ApplicationRepository.cs
    │   │   └── Configurations/
    │   │       ├── IConfigurationRepository.cs
    │   │       └── ConfigurationRepository.cs
    │   ├── Models/
    │   │   ├── Common/
    │   │   │   └── BaseModel.cs               # ported: Id, CreatedDate — used by Application only
    │   │   ├── Applications/
    │   │   │   └── Application.cs
    │   │   └── Configurations/
    │   │       └── Configuration.cs
    │   ├── Exceptions/
    │   │   ├── Common/
    │   │   │   └── ValidationException.cs
    │   │   ├── Applications/
    │   │   │   ├── ApplicationNotFoundException.cs
    │   │   │   └── DuplicateApplicationNameException.cs
    │   │   └── Configurations/
    │   │       ├── ConfigurationNotFoundException.cs
    │   │       └── DuplicateConfigurationKeyException.cs
    │   ├── Infrastructure/
    │   │   └── DynamoDb/
    │   │       ├── DynamoDbSettings.cs
    │   │       ├── DynamoDbJsonSerializer.cs
    │   │       ├── DynamoDbTableCache.cs
    │   │       ├── IDynamoDbCollection.cs               # ported as-is: single partition-key `id`
    │   │       ├── DynamoDbCollection.cs                # ported as-is
    │   │       ├── IDynamoDbCompositeKeyCollection.cs   # NEW — required by the spec's composite key; see §2 callout
    │   │       └── DynamoDbCompositeKeyCollection.cs    # NEW — see §2 callout
    │   ├── Middleware/
    │   │   └── ErrorMiddleware.cs
    │   └── Ignition/
    │       ├── DynamoDbIgnition.cs
    │       ├── RepositoryIgnition.cs
    │       ├── ServicesIgnition.cs
    │       └── LogIgnition.cs
    └── ConfigApi.Service.UnitTests/
        ├── ConfigApi.Service.UnitTests.csproj
        ├── coverlet.runsettings
        ├── GlobalUsings.Controllers.cs
        ├── GlobalUsings.Services.cs
        ├── GlobalUsings.Repositories.cs
        ├── GlobalUsings.Models.cs
        ├── GlobalUsings.Exceptions.cs
        ├── Controllers/
        │   ├── ApplicationsControllerTests.cs
        │   └── ConfigurationsControllerTests.cs
        ├── Services/
        │   ├── ApplicationServiceTests.cs
        │   └── ConfigurationServiceTests.cs
        ├── Repositories/
        │   ├── ApplicationRepositoryTests.cs
        │   └── ConfigurationRepositoryTests.cs
        └── Ignition/
            ├── RepositoryIgnitionTests.cs
            └── ServiceIgnitionTests.cs
```

Note: income-service's own two `GlobalUsings.*` conventions are slightly inconsistent (main project folder is `Ignition/`, test folder is `Ignitions/`; `GlobalUsings.Controllers.cs` lists only one namespace instead of all of them). Standardized on `Ignition/` in both projects, and every `GlobalUsings.<Layer>.cs` lists all subnamespaces of that layer.

**Scope note (post-review):** the original draft of this plan also proposed separate `CreateApplicationRequest`/`UpdateApplicationRequest`/`CreateConfigurationRequest`/`UpdateConfigurationRequest` DTO classes and an `UpdatedDate` field on both entities. Neither is in the spec, and income-service itself binds controller actions directly to the entity type (`Create([FromBody] Contact model)`). Per "only build what the spec/plan calls for," those DTOs and the extra field are **cut** — controllers bind directly to `Application`/`Configuration`, matching the reference project.

---

## 2. Architectural approach per layer

**Controller** — thin MVC controllers (`[ApiController]`, `ControllerBase`), one domain per file under `Controllers/<Domain>/`, routed under `api/v1/...`. They depend only on an `I<Domain>Service`, do no DynamoDB- or persistence-aware work, and translate `null` return values to `NotFound()` / `201 Created` / `204 NoContent`. Domain exceptions are **not** caught in controllers (except where a controller-local mapping is clearer, mirroring `ContactsController`'s occasional local `catch (KeyNotFoundException)`); the default path is to let exceptions bubble to `ErrorMiddleware`.

`HealthController` is the one exception to the `/api/v1` prefix — routed at `GET /health` (not `/api/v1/health`), matching the spec's exact path. It has no service/repository dependency and returns `Ok(new { status = "healthy" })`; it exists to verify the deployed service is reachable independent of DynamoDB connectivity.

**Service** — `Services/<Domain>/I<Domain>Service.cs` + `<Domain>Service.cs`, holds business rules: existence checks, the applications↔configurations foreign-key-equivalent validation, duplicate-key rejection, and request→entity mapping. Services depend only on repository interfaces (never on `IAmazonDynamoDB`/`IDynamoDbCollection<T>` directly) — this is the seam that makes them Moq-testable without touching AWS.

**Repository** — `Repositories/<Domain>/I<Domain>Repository.cs` + `<Domain>Repository.cs`, one per entity, each wrapping exactly one `IDynamoDbCollection<T>` (Applications) or `IDynamoDbCompositeKeyCollection<T>` (Configurations — see callout below). Repositories expose **domain-shaped** methods (`GetAll()`, `GetById(id)`, `CreateAsync(entity)`, …), never leak `AttributeValue`/`Document` types, exactly like `ContactRepository` wrapping `IDynamoDbCollection<Contact>`.

**Ignition** — static extension-method classes under `Ignition/`, called once from `Program.cs`, each responsible for one DI concern: `DynamoDbIgnition` (SDK client + table-scoped collections), `RepositoryIgnition` (repository bindings), `ServicesIgnition` (service bindings), `LogIgnition` (Serilog). This is a verbatim structural copy of income-service's pattern, minus the unrelated `AuthenticationIgntion`/`AuthorizationIgnition`/`RateLimitIgnition`/`AnalyticsIgnition` — no auth/rate-limiting/analytics are in this spec's scope.

**Exceptions** — domain-grouped folders (`Exceptions/Applications`, `Exceptions/Configurations`, `Exceptions/Common`), one exception type per failure mode, each a small subclass of `Exception` with a message-only constructor (mirrors `IncomeRecordNotFoundException`, `EmailSendException`). `ValidationException` carries an `IReadOnlyDictionary<string,string> Errors` field, mirroring income-service's `ExpenseValidationException`.

**GlobalUsings** — one file per layer folder at the project root, each a flat list of `global using ConfigApi.Service.<Layer>.<Domain>;` lines for every subnamespace of that layer, so a file inside `Controllers/Configurations/` can reference `Application` (from `Models/Applications`) or `ApplicationNotFoundException` (from `Exceptions/Applications`) without a local `using`.

### Composite-key collection abstraction — required, not optional

income-service's `IDynamoDbCollection<T>` (`GetById(string id)`, `DeleteOneAsync(string? id)`, etc.) is hard-wired to a single partition key named `id` — every one of its 16 production tables uses that shape; none has a sort key. The spec's `configurations` table requires partition key `applicationId` **plus** sort key `configKey`, which that interface cannot express, so this is not scope creep — it's what the spec's own key design requires:

```csharp
public interface IDynamoDbCompositeKeyCollection<T> where T : class
{
    IQueryable<T> AsQueryable();
    T? GetByKey(string partitionKeyValue, string sortKeyValue);
    Task<T?> GetByKeyAsync(string partitionKeyValue, string sortKeyValue, CancellationToken ct = default);
    Task InsertOneAsync(T item);
    Task<bool> ReplaceOneAsync(T item, bool upsert = false);
    Task<bool> DeleteOneAsync(string partitionKeyValue, string sortKeyValue);
}
```

`DynamoDbCompositeKeyCollection<T>` reuses the same `DynamoDbTableCache` (Scan-once-per-request, TTL-cached, invalidate-on-write) and the same `Document.FromJson`/`ToAttributeMap()` round-trip as `DynamoDbCollection<T>` — only the key-building and `GetItem`/`DeleteItem` request shape differ (two-attribute `Key` dictionary instead of one). It takes the partition/sort key **attribute names** and two `Func<T,string>` accessors in its constructor (e.g. `"applicationId"`, `c => c.ApplicationId`, `"configKey"`, `c => c.ConfigKey`) rather than requiring a shared base class, so `Configuration` doesn't need to inherit `BaseModel`'s single-`Id` shape.

---

## 3. Entity shapes and DynamoDB mapping

**`Application`** (table `applications`, PK `id` String) — inherits `BaseModel` (`Id`, `CreatedDate`) exactly like `Contact`:

```csharp
public record Application : BaseModel
{
    public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
}
```

Controllers bind directly to `Application` on create/update and return it directly on success — matches income-service's `Create([FromBody] Contact model)` pattern. No separate request DTOs (cut per the scope note in §1).

**`Configuration`** (table `configurations`, PK `applicationId` String, SK `configKey` String) — does **not** inherit `BaseModel` (no single `Id`; the entity's identity is the `(applicationId, configKey)` pair):

```csharp
public record Configuration
{
    public string ApplicationId { get; set; } = string.Empty;
    public string ConfigKey { get; set; } = string.Empty;
    public string Value { get; set; } = string.Empty;
    public string? Description { get; set; }
    public DateTime CreatedDate { get; set; }
}
```

`Value` is a plain `string`.

This directly satisfies "every configuration entry belongs to exactly one application, with `applicationId` as a required foreign-key-equivalent reference": the DynamoDB partition key **is** that reference, and `ConfigurationService.CreateAsync` additionally verifies the parent `Application` exists (via `IApplicationRepository.GetById`) before the write, throwing `ApplicationNotFoundException` → 404 if not — there is no DynamoDB-native FK constraint, so this check is the enforcement point, same spirit as `ContactRepository.AnyForOrganisation` guards in income-service.

Naming (`configKey` as the Configurations sort key) is directly consistent with the spec's forward-looking `flags` table (`applicationId` PK + `flagKey` SK) — same `<entity>Key` sort-key convention, same partition key name, so `IDynamoDbCompositeKeyCollection<T>` and `Repositories/Flags` can be added in Module 3 with no shape rework.

---

## 4. DynamoDB provisioning under `infra/`

income-service itself has no committed provisioning script — its `docs/dynamodb.md` says new tables are created by hand via the AWS console. `infra/ConfigApi.Provisioning/` is a small `net10.0` console project (own `.csproj`, not part of the API's dependency surface) referencing only `AWSSDK.DynamoDBv2` and `DotNetEnv` — both already approved — plus BCL. It is the DynamoDB analogue of a numbered SQL migrations folder:

- `Migrations/ITableMigration.cs` — `{ int Version; string Description; Task ApplyAsync(IAmazonDynamoDB client); }`
- `Migrations/0001_CreateApplicationsTable.cs` — `applications`, PK `id` (S), `BillingMode.PAY_PER_REQUEST`, PITR left disabled (AWS default)
- `Migrations/0002_CreateConfigurationsTable.cs` — `configurations`, PK `applicationId` (S) + SK `configKey` (S), same billing mode
- Each migration is idempotent: `DescribeTable` first; on `ResourceNotFoundException`, `CreateTable`; otherwise log "already exists, skipping."
- Numbering convention (documented in `infra/README.md`): four-digit, strictly increasing, never edited once merged. `0003` is reserved in the doc (not implemented) for the Module 3 `flags` table.
- Run via `dotnet run --project infra/ConfigApi.Provisioning` from the repo root; loads the same root `.env` via `DotNetEnv.Env.Load()` before touching AWS.

---

## 5. Dependency injection setup (`Ignition/*.cs`)

Mirrors income-service's `Program.cs` call order (`ConfigureLogging` → `ConfigureDynamoDb` → `ConfigureRepositories` → `ConfigureServices`) minus the auth/rate-limit/analytics ignitions that don't apply here:

```csharp
// Program.cs
DotNetEnv.Env.Load();                       // must run before builder reads configuration
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddOpenApi();

builder.ConfigureLogging();                 // LogIgnition
builder.ConfigureDynamoDb();                // DynamoDbIgnition
builder.Services.ConfigureRepositories();   // RepositoryIgnition
builder.Services.ConfigureServices();       // ServicesIgnition

var app = builder.Build();

if (app.Environment.IsDevelopment())        // spec: Scalar "enabled in the dev environment"
{
    app.MapOpenApi();
    app.MapScalarApiReference();
}

app.UseSerilogRequestLogging();
app.UseMiddleware<ErrorMiddleware>();
app.MapControllers();
app.Run();
```

- **`DynamoDbIgnition.ConfigureDynamoDb(this WebApplicationBuilder builder)`** — binds `DynamoDbSettings` from the `"DynamoDB"` config section, `AddMemoryCache()`, registers `DynamoDbTableCache` scoped, registers `IAmazonDynamoDB` as a singleton, then `RegisterCollection<Application>(builder, "applications")` and `RegisterCompositeKeyCollection<Configuration>(builder, "configurations", "applicationId", c => c.ApplicationId, "configKey", c => c.ConfigKey)`.

  **Credential-chain nuance vs. income-service:** income-service builds `new AmazonDynamoDBClient(accessKey, secretKey, RegionEndpoint...)` by reading custom `DYNAMODB_*` keys out of `IConfiguration` directly — it does not rely on the SDK's default credential chain. This spec explicitly says credentials are "picked up by the standard AWS SDK credential chain," so `DynamoDbIgnition` here uses `new AmazonDynamoDBClient(RegionEndpoint.GetBySystemName(region))` — letting the SDK's built-in `EnvironmentVariablesAWSCredentials` resolve `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` itself — with only the region passed explicitly (read from `AWS_REGION`, defaulting to `ap-southeast-6`). `.env.example` uses the SDK's own recognized variable names (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`), not income-service's custom names.

- **`RepositoryIgnition.ConfigureRepositories(this IServiceCollection services)`** — `AddScoped<IApplicationRepository, ApplicationRepository>()`, `AddScoped<IConfigurationRepository, ConfigurationRepository>()`.
- **`ServicesIgnition.ConfigureServices(this IServiceCollection services)`** — `AddScoped<IApplicationService, ApplicationService>()`, `AddScoped<IConfigurationService, ConfigurationService>()`.
- **`LogIgnition.ConfigureLogging(this WebApplicationBuilder builder)`** — verbatim copy of income-service's Serilog console setup.

`appsettings.json` `"DynamoDB"` section:
```json
"DynamoDB": {
  "TableNames": { "applications": "applications", "configurations": "configurations" },
  "ScanCacheSeconds": 300
}
```

---

## 6. Error handling / exception strategy

`Middleware/ErrorMiddleware.cs` is a direct structural copy of income-service's: cascading `catch` blocks (most specific first), each mapping one exception type to an HTTP status code and a JSON `{ status, title, detail, error, exceptionType, traceId }` body, 5xx bodies generic, 4xx bodies keep the caller-facing message:

| Exception | Status | Notes |
|---|---|---|
| `ApplicationNotFoundException` | 404 | missing `id`; also thrown by `ConfigurationService` when the parent application doesn't exist |
| `ConfigurationNotFoundException` | 404 | missing `(applicationId, configKey)` |
| `DuplicateApplicationNameException` | 409 | `POST /api/v1/applications` with a `name` that already exists |
| `DuplicateConfigurationKeyException` | 409 | `POST` with a `configKey` that already exists under that application |
| `ValidationException` | 400 | carries `Errors` dictionary |
| `ArgumentException` / `ArgumentNullException` | 400 | generic bad-input fallback |
| everything else | 500 | generic body, real exception logged via Serilog |

Registered via `app.UseMiddleware<ErrorMiddleware>()` in `Program.cs`, before `MapControllers()`.

---

## 7. Testing strategy (`ConfigApi.Service.UnitTests`)

Structure mirrors `Controllers/`, `Services/`, `Repositories/`, `Ignition/` 1:1 with the main project, per spec. `.csproj` copies income-service's test project settings: `IsTestProject=true`, `FrameworkReference Include="Microsoft.AspNetCore.App"`, `xunit` + `xunit.runner.visualstudio` + `Moq` + `coverlet.collector`/`coverlet.msbuild`, `ProjectReference` to the main project, `InternalsVisibleTo` from the main `.csproj`.

**Repository tests** — mock the collection interface, not AWS, exactly like `ContactRepositoryTests.CreateRepo`. `ConfigurationRepositoryTests` mock `IDynamoDbCompositeKeyCollection<Configuration>`, with `GetByKey(applicationId, configKey)` and `DeleteOneAsync(applicationId, configKey)` setups.

**Service tests** — mock `I{X}Repository` via Moq; assert business rules: `ConfigurationServiceTests` covers "throws `ApplicationNotFoundException` when the parent application repo returns null," "throws `DuplicateConfigurationKeyException` on a second `CreateAsync` with the same key," "propagates a valid create."

**Controller tests** — mock `I{X}Service` via Moq; assert `ActionResult` shape (`OkObjectResult`, `NotFoundResult`, `CreatedResult` with the right `Location`, `NoContentResult`).

**Ignition tests** — `RepositoryIgnitionTests`/`ServiceIgnitionTests` assert `IServiceCollection` registrations by service/implementation type and lifetime. `DynamoDbIgnition` itself is excluded from coverage (touches real AWS SDK client construction), mirrored in `coverlet.runsettings`:
```xml
<Exclude>[ConfigApi.Service]Infrastructure.DynamoDb.*,[ConfigApi.Service]Ignition.DynamoDbIgnition</Exclude>
<ExcludeByFile>**/obj/**%2c**/Program.cs</ExcludeByFile>
```

---

## 8. API documentation (`Microsoft.AspNetCore.OpenApi` + `Scalar.AspNetCore`)

`builder.Services.AddOpenApi()` in `Program.cs` (no security-scheme transformer — no auth in scope). `app.MapOpenApi()` + `app.MapScalarApiReference()` are called only inside `if (app.Environment.IsDevelopment())`, since the spec says "enabled in the dev environment." `[ProducesResponseType]` attributes on every controller action (200/201/204/400/404/409 as applicable) so the generated schema documents error responses too. This is the mechanism the spec calls out for exercising full CRUD on both resources against the real provisioned tables without a separate client.

---

## 9. Logging (`Serilog.AspNetCore`)

`LogIgnition.ConfigureLogging` wires `builder.Host.UseSerilog(...)` with `Enrich.FromLogContext()`, `MinimumLevel.Information()`, `MinimumLevel.Override("Microsoft", LogEventLevel.Warning)`, `WriteTo.Console()`. `app.UseSerilogRequestLogging()` added to `Program.cs`. `ErrorMiddleware` logs every handled exception via injected `ILogger<ErrorMiddleware>` before writing the response.

---

## 10. Sequencing of implementation steps

1. **Scaffold** — `global.json`, `.sln` (3 projects), both `.csproj` files with only approved packages, `Nullable`/`ImplicitUsings`/`TreatWarningsAsErrors` set, `.gitignore` additions (`.env`, `bin/`, `obj/`), `.env.example`.
2. **Infrastructure/DynamoDb layer** — `DynamoDbSettings`, `DynamoDbJsonSerializer`, `DynamoDbTableCache`, `IDynamoDbCollection<T>`/`DynamoDbCollection<T>` (ported), then `IDynamoDbCompositeKeyCollection<T>`/`DynamoDbCompositeKeyCollection<T>`.
3. **Models** — `BaseModel`, `Application`, `Configuration`, `GlobalUsings.Models.cs`.
4. **Exceptions + `ErrorMiddleware`** — domain exception types, `GlobalUsings.Exceptions.cs`, middleware wired to the exception set from step 3.
5. **Repositories** — `IApplicationRepository`/`ApplicationRepository`, `IConfigurationRepository`/`ConfigurationRepository`, `GlobalUsings.Repositories.cs`.
6. **`Ignition/DynamoDbIgnition.cs` + `Ignition/RepositoryIgnition.cs`** — first point the app can resolve a repository end-to-end against real DynamoDB.
7. **Services** — `IApplicationService`/`ApplicationService`, `IConfigurationService`/`ConfigurationService` (FK-equivalent existence check, duplicate-key rejection), `GlobalUsings.Services.cs`, `Ignition/ServicesIgnition.cs`.
8. **Controllers** — `HealthController`, `ApplicationsController`, `ConfigurationsController`, `GlobalUsings.Controllers.cs`.
9. **`Ignition/LogIgnition.cs` + `Program.cs`** — wires every ignition together, OpenAPI/Scalar (dev-only), Serilog request logging, `ErrorMiddleware` registration.
10. **`infra/ConfigApi.Provisioning`** — can be built any time after step 1; must be **run** against the real AWS account before step 12's manual verification.
11. **`ConfigApi.Service.UnitTests`** — scaffold csproj/`coverlet.runsettings`/GlobalUsings, then write tests layer-by-layer alongside (or immediately after) steps 5, 7, 8.
12. **Manual end-to-end verification** — run the provisioning script, run the API in `Development`, exercise every CRUD endpoint for both resources via Scalar against the real `applications`/`configurations` tables, including negative paths (`POST` a configuration under a nonexistent `applicationId` → 404; duplicate `configKey` → 409).
13. **README** — `.env` setup, provisioning command, run command, Scalar URL, `dotnet test` command.

Hard dependency chain: 2 → 3 → {4, 5} → 6 → 7 → 8 → 9. Step 10 (infra) is independent of the C# app code and can run in parallel with steps 2–9, but must complete before step 12.

---

## 11. Decisions (resolved, minimal-scope bias)

The spec is silent on these. Resolved in favor of the smallest behavior that satisfies the spec, rather than adding unrequested logic:

1. **Cascade behavior on `DELETE /applications/{id}`** when configurations exist for it: **reject with 409.** Cascade-deleting is extra logic the spec never asked for; rejecting is simpler and safer, and mirrors income-service's guard-before-delete pattern (`AnyForOrganisation`).
2. **`configKey` character set** — alphanumeric plus `.`, `_`, `-` (no `/`), validated in `ConfigurationService` since it's a raw path segment.
3. **List endpoint pagination** — unpaginated full-table Scan for both list endpoints, matching income-service's existing Scan-and-cache model. No pagination logic added since the spec doesn't ask for it.
4. **`Application.Name` uniqueness** — **enforced**: `ApplicationService.CreateAsync` scans existing applications for a case-sensitive name match (via `IApplicationRepository.GetByName`, implemented over the existing cached `AsQueryable()` — no GSI needed) and throws a new `DuplicateApplicationNameException` (409) if found, before insert. `id` remains the technical identity; `name` is a uniqueness constraint enforced at the service layer, matching the course's reference Python example's `409` behavior on `POST /applications`.
5. **Provisioning tool approach (§4)** — small C# console project, since it reuses already-approved packages and needs no extra local tooling beyond the .NET SDK already required.

Authentication is intentionally out of scope: the approved dependency list has no auth package (income-service's `Microsoft.AspNetCore.Authentication.JwtBearer` is not on it), and the spec never asked for it — so no auth is being added.

---

### Critical Files for Implementation

- `C:\dev\assisted-to-agentic-course-work\assisted-to-agentic-module-1\config-service\src\ConfigApi.Service\Infrastructure\DynamoDb\DynamoDbCompositeKeyCollection.cs` (new abstraction; everything Configurations-related depends on it)
- `C:\dev\assisted-to-agentic-course-work\assisted-to-agentic-module-1\config-service\src\ConfigApi.Service\Ignition\DynamoDbIgnition.cs`
- `C:\dev\assisted-to-agentic-course-work\assisted-to-agentic-module-1\config-service\src\ConfigApi.Service\Services\Configurations\ConfigurationService.cs` (FK-equivalent + duplicate-key enforcement lives here)
- `C:\dev\assisted-to-agentic-course-work\assisted-to-agentic-module-1\config-service\src\ConfigApi.Service\Middleware\ErrorMiddleware.cs`
- `C:\dev\assisted-to-agentic-course-work\assisted-to-agentic-module-1\config-service\infra\ConfigApi.Provisioning\Program.cs`
- `C:\dev\assisted-to-agentic-course-work\assisted-to-agentic-module-1\config-service\src\ConfigApi.Service\Program.cs`
