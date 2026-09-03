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
- **Reflections**: The assistant followed the preamble instructions closely — it reorganized the spec into a directive prompt aimed at an implementation-plan-generating assistant, preserved every constraint verbatim (approved dependency list, `income-service` architectural pattern, DynamoDB table/key schema, forward-looking `flags` table note), and added an explicit "ask before assuming" instruction plus a numbered list of what the plan output should contain. It did not invent any new technical decisions or add dependencies, which was the main risk to watch for at this step. After the first pass, iterated directly on both `1-web-api-specs.md` and `2-web-api-prompt.md` (before committing) to: move the DynamoDB region from `us-east-1` to `ap-southeast-6` (Asia Pacific / New Zealand — confirmed via the AWS account as an opted-in region with DynamoDB available), add `DotNetEnv` + a local git-ignored `.env` file as the AWS credential source, and require the service to be fully workable end-to-end with Scalar UI enabled for manual testing.
