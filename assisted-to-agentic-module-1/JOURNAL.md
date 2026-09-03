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
