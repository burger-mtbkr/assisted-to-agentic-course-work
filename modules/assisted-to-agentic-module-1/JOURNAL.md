# Module 1 Journal

Collaboration log for the Configuration API Service exercise. One entry per
meaningful AI collaboration, using the template below.

## Entry template

- **Prompt**:
- **Tool**:
- **Mode**:
- **Context**:
- **Model**:
- **Input**:
- **Output**:
- **Cost**:
- **Reflections**:

## Entries

### 1. Spec → implementation-plan prompt

- **Prompt**: Read @/prompts/1-web-api-specs.md and follow the instructions at the top of the file.
- **Tool**: Claude Code
- **Mode**: Plan
- **Context**: Clean
- **Model**: claude-sonnet-5
- **Input**: `prompts/1-web-api-specs.md`
- **Output**: `prompts/2-web-api-prompt.md`
- **Cost**: Not separately metered in this environment (subscription-based Claude Code session, no per-call token/dollar figure surfaced).
- **Reflections**: The assistant followed the preamble instructions closely — it reorganized the spec into a directive prompt aimed at an implementation-plan-generating assistant, preserved every constraint verbatim (approved dependency list, `income-service` architectural pattern, DynamoDB table/key schema, forward-looking `flags` table note), and added an explicit "ask before assuming" instruction plus a numbered list of what the plan output should contain. It did not invent any new technical decisions or add dependencies, which was the main risk to watch for at this step. After the first pass, iterated directly on both `1-web-api-specs.md` and `2-web-api-prompt.md` (before committing) to: move the DynamoDB region from `us-east-1` to `ap-southeast-6` (Asia Pacific / New Zealand — confirmed via the AWS account as an opted-in region with DynamoDB available), add `DotNetEnv` + a local git-ignored `.env` file as the AWS credential source, and require the service to be fully workable end-to-end with Scalar UI enabled for manual testing. Also added a `GET /health` endpoint requirement, learned partway through review that it was missing.

### 2. Prompt → implementation plan

- **Prompt**: Read @/prompts/2-web-api-prompt.md and follow the instructions at the top of the file.
- **Tool**: Claude Code
- **Mode**: Plan
- **Context**: Clean
- **Model**: claude-sonnet-5
- **Input**: `prompts/2-web-api-prompt.md`
- **Output**: `prompts/3-web-api-plan.md`
- **Cost**: Not separately metered in this environment.
- **Reflections**: This step surfaced the most useful learning of the exercise so far. The prompt told the assistant to ask clarifying questions rather than guess if it wasn't familiar with `income-service`'s conventions — instead, since this was a one-shot run with no one to answer follow-ups, it used WebFetch to actually pull the real `income-service` source (Program.cs, Ignition/*.cs, a representative repository/controller pair, the Exceptions folder, both .csproj files) and grounded the plan in what it found rather than inventing a plausible-sounding structure. That's a meaningfully different (better) outcome than a plan built from pattern-matching alone.

  It also caught a real architectural gap I hadn't thought through: `income-service`'s `IDynamoDbCollection<T>` abstraction is hard-wired to a single partition key called `id` — every one of its tables uses that shape. Our `configurations` table needs a partition key (`applicationId`) *and* a sort key (`configKey`), which that interface can't express. The plan proposes a sibling `IDynamoDbCompositeKeyCollection<T>` abstraction rather than forcing the composite key into the existing shape. This isn't scope creep — it's a genuine requirement of the spec's own key design — but it is new code with no precedent to copy, so it's flagged as needing sign-off before Step 5 rather than being built unreviewed.

  On the other hand, the first draft *did* overreach in a couple of places the spec never asked for: separate `Create`/`Update` request DTOs per entity (when `income-service` itself just binds directly to the entity type) and an `UpdatedDate` field on both models. Caught this on review and cut both — controllers now bind directly to `Application`/`Configuration`, matching the reference project exactly. Good reminder that "grounded in a real reference project" and "scope-disciplined" aren't the same thing; the plan needed both a research pass and a trim pass.

  Also resolved the one open decision the plan flagged as blocking (cascade-delete behavior on `DELETE /applications/{id}` when configurations exist) by picking the smaller-scope option — reject with 409 rather than cascade — instead of leaving it for the Step 5 coding assistant to decide on its own.

### 3. Plan → implementation (`config-service/` scaffold)

- **Prompt**: Please create a Config API Service in the config-service folder, according to the Implementation Plan defined in @/prompts/3-web-api-plan.md
- **Tool**: Claude Code
- **Mode**: Act
- **Context**: Clean (delegated to a subagent with only the plan file — no memory of the rest of this conversation)
- **Model**: claude-sonnet-5
- **Input**: `prompts/3-web-api-plan.md`
- **Output**: `config-service/` (initial scaffold — 44 files)
- **Cost**: Not separately metered in this environment. The build subagent's own run used ~171k tokens and 123 tool calls over ~14 minutes.
- **Reflections**: This was the step where "not writing the code directly" felt most real. The scaffolding agent produced all 44 files from the plan's §1 tree exactly, self-corrected two deviations it wasn't allowed to make (a missing `openapi.json` — blocked by the "don't run the service, don't add unapproved packages" constraints — and a missing `.env` — no real credentials to put in it), and flagged both clearly instead of silently working around them or inventing a workaround. `dotnet build`/`dotnet test` were clean before I even looked at the code (44/44 passing). Also incorporated mid-flight, via a follow-up message to the running agent: `Application.Name` uniqueness enforcement (409 on duplicate), added after comparing behavior against the course's reference example (see Entry 5) while the scaffold was still in progress.

  Separately, before this ran: created a dedicated IAM user (`config-service-local-dev`) with an inline policy scoped to only `GetItem`/`PutItem`/`UpdateItem`/`DeleteItem`/`Query`/`Scan`/`DescribeTable`/`CreateTable`/tagging on just the two `applications`/`configurations` tables, and generated its access key for local `.env` use — declined to use the AWS account's root credentials even though that would have been the path of least resistance (the account's caller identity turned out to be the literal root user, `arn:aws:iam::...:root`).

### 4. Live verification, bug fix, and test-coverage collaboration

- **Prompt**: "Once done, ensure full scenario and endpoint test coverage and full unit test coverage. Test it yourself — do full synthetic testing. Once everything works, commit and push. Only the DB is deployed, the API only runs locally. `dotnet run` should land on the Scalar page. Remember the AWS connection details for DynamoDB in the env file." (paraphrased from the live instruction; typos in the original corrected here for readability)
- **Tool**: Claude Code
- **Mode**: Act
- **Context**: Continued (same session as Entry 3, not a clean context — direct collaborative debugging rather than a delegated one-shot run)
- **Model**: claude-sonnet-5
- **Input**: the scaffolded `config-service/` from Entry 3, plus the real AWS DynamoDB tables
- **Output**: bug fixes to `Infrastructure/DynamoDb/{DynamoDbCollection,DynamoDbCompositeKeyCollection}.cs`, new tests (`ErrorMiddlewareTests.cs`, `HealthControllerTests.cs`, added `UpdateAsync` success-path cases), a root→Scalar redirect in `Program.cs`, `openapi.json`, populated `.env`
- **Cost**: Not separately metered in this environment.
- **Reflections**: "Tests pass" and "the feature actually works" turned out to be two different claims. Before touching anything else, I ran the whole thing for real: checked the provisioning script against the live tables (idempotent, correct), started the service, and hit every endpoint with curl against the real DynamoDB tables in `ap-southeast-6`. First run failed immediately — every single request, including a plain `GET /api/v1/applications`, returned `400 ArgumentOutOfRangeException: A hash key definition is required, call AddHashKey before Build.` The unit tests were 100% green because they mock `IDynamoDbCollection<T>`/`IDynamoDbCompositeKeyCollection<T>` at the boundary — nothing in the suite ever actually constructed a `TableBuilder` against a real client, so this bug was invisible to `dotnet test` no matter how much coverage it had. Both `DynamoDbCollection<T>` and `DynamoDbCompositeKeyCollection<T>` called `new TableBuilder(client, tableName).Build()` without ever specifying the key schema. Fixed by adding explicit `.AddHashKey(...)` (and `.AddRangeKey(...)` for the composite case) before `.Build()` — recorded in this module's `AGENTS.md` so it isn't rediscovered next time.

  After the fix, ran the complete scenario matrix by hand against the live service and real tables: application CRUD (create, duplicate-name 409, get, 404-on-missing, update, list), configuration CRUD nested under an application (create, duplicate-key 409, create-under-missing-application 404, get, 404-on-missing, update, list), the cascade-delete-rejection behavior (409 while children exist, 204 once they're gone, repeat-delete 404), and confirmed the DynamoDB tables were back to 0 items after cleanup — every scenario matched the plan's documented behavior exactly. Also confirmed `GET /health`, the `/` → `/scalar` redirect (added specifically because `dotnet run` landing on a 404 root wasn't otherwise guaranteed), and the static `openapi.json` export generated from the live OpenAPI document.

  Reviewing the generated test suite against this same scenario list caught a second class of gap: `ErrorMiddleware` (the exception → HTTP status mapping — the thing that actually makes those 404s and 409s happen) had zero test coverage, despite being core cross-cutting behavior. Also missing: any test for `HealthController`, and the success-path branch of both `ApplicationService.UpdateAsync`/`ConfigurationService.UpdateAsync` (only their not-found branches were tested). Added all of the above — 55/55 tests passing afterward, and every business-logic class shows 100% line coverage in the cobertura report (the only 0%-coverage classes left are the ones the plan's own `coverlet.runsettings` deliberately excludes: the DynamoDB SDK wrapper classes and `Program.cs`, which touch a real AWS client and were exercised by the live synthetic testing instead). This is the clearest evidence from the whole exercise for why "the assistant reports tests pass" and "the feature works" are not substitutes for each other — a green test suite told me nothing about a bug in the exact code path the tests were mocking around.

### 5. Reference-example comparison

- **Prompt**: "Ensure our API functionality matches the example if it's valid based on the instructions." Plus a follow-up requesting a static OpenAPI spec file at the service root.
- **Tool**: Claude Code
- **Mode**: Plan (discussion/comparison, no file changes until decisions were confirmed)
- **Context**: Continued
- **Model**: claude-sonnet-5
- **Input**: `examples/config-service/svc` (the course's Python/FastAPI/Postgres reference implementation)
- **Output**: updated `prompts/1-web-api-specs.md` / `2-web-api-prompt.md` / `3-web-api-plan.md` (name-uniqueness requirement, static `openapi.json` requirement)
- **Cost**: Not separately metered in this environment.
- **Reflections**: Reading the reference example's `endpoints.py`/`schemas.py` surfaced a genuinely different design: it models "configuration" as a single JSON blob per application (`PUT /applications/{id}/config` replaces the whole thing), not individual key/value entries like our spec. Rather than silently either ignoring the example or blindly copying it, laid out the fork explicitly and asked: keep our multi-entry model (better fit for the Module 3 `flags` extension, and already mid-build) or switch to match the example exactly. Decision: keep our model, but adopt one specific behavior the example got right that our plan hadn't considered — 409 on duplicate application name — since that's a legitimate functional gap, not a data-model disagreement. This is the clearest example in the whole exercise of the course's own instruction that examples are "useful only as a structural template... not as a tech choice" — the reference was genuinely useful for finding a missed requirement, without needing to be copied wholesale.
