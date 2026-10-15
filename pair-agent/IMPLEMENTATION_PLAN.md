# PAIR Agent - Implementation Plan

Step 0 of `modules/assisted-to-agentic-module-6/project/STEPS.md`: the plan
for this repo's PAIR Agent, written against `project/DESIGN.md` before any
code.

## Decisions STEPS.md asks for

| Question | Answer |
|---|---|
| Provider | **Google Gemini** (`gemini-flash-latest`, the free-tier Flash model) through Google's OpenAI-compatible chat endpoint, called with `httpx` - no SDK. `GEMINI_API_KEY` comes from the environment or a git-ignored `pair-agent/.env`; it is never committed. |
| Where `mcp.json` lives | `pair-agent/mcp.json`, same `mcpServers` shape as the repo's `.mcp.json` plus an optional `cwd` (resolved relative to `mcp.json`). It starts the Module 5 `domain-lang` server. |
| Where skills live | The repo's existing `.claude/skills/` (`PAIR_AGENT_SKILLS_DIR` to override). DESIGN.md recommends `.agents/skills`; copying the Module 4 skills there would give two copies that drift, and Claude Code only reads `.claude/skills`. One source of truth wins; the directory is a setting, not a convention baked into code. |
| Files | See layout below. |
| Run and test | `uv run --project pair-agent pair-agent` from the repo root; `uv run --project pair-agent pytest pair-agent`. Manual validation against real Gemini Flash, transcripts saved with `/save`. |

## Why it lives at the repo root, beside `config-service/`

Repo anchoring. Its default code directory is `../config-service`, its
system prompt includes `config-service/AGENTS.md`, its skills are this
repo's, and its MCP reads `config-service/knowledge/`. Like
`domain-lang-mcp/`, it spans modules, so it sits at the root rather than
inside `modules/assisted-to-agentic-module-6/`.

## Layout

```text
pair-agent/
  mcp.json
  src/pair_agent/
    cli.py         # startup wiring, REPL, /tools /messages /save /load /reset /quit
    agent.py       # messages array + the conversation/tool loop
    provider.py    # Gemini chat API: translate messages + tools, call, parse
    tools.py       # ToolRegistry + harness-owned repo tools (read_file, search_code)
    skills.py      # SkillCatalog: discover metadata, activate, run bundled script
    mcp_client.py  # read mcp.json, start servers, discover + call tools
    prompt.py      # effective system prompt
  tests/
```

## The messages array

Provider-neutral, plain dicts, so `/messages` shows the agent's working
memory as it is:

```text
{"role": "system",    "content": str}
{"role": "user",      "content": str}
{"role": "assistant", "content": str, "tool_calls": [{"id", "name", "arguments"}]}
{"role": "tool",      "tool_call_id": str, "name": str, "content": str, "is_error": bool}
```

The provider seam translates this to the chat-completions format on every
call: `tool_calls` become `function` calls with JSON-string arguments, and
`tool` messages carry their `tool_call_id`. Gemini's per-call "thought
signature" (`extra_content`) is stored on the call and sent back with it.
Swapping providers means one new translator, not a new loop.

## Build order (STEPS.md 1-7)

1. **Conversation** - `provider.py`, a bare `agent.py` loop, `cli.py` REPL.
   Validate: multi-turn recall.
2. **Tool loop** - `ToolRegistry`; loop executes requested tools, appends
   `tool` messages, calls the model again until it answers without tools
   (cap: `PAIR_AGENT_MAX_TOOL_ROUNDS`, default 12). First tool:
   `read_file`. Validate: a question that needs a file read.
3. **MCP** - `mcp_client.py` with the official SDK's client (stdio). Tools
   registered as `mcp__<server>__<tool>` (Claude Code's convention, keeps
   provenance visible and names collision-free). Validate: "What does
   ConfigurationItem mean in this system?" -> `mcp__domain-lang__lookup_term`.
4. **Skill discovery** - `SkillCatalog` reads only YAML frontmatter
   (`name`, `description`) at startup; `list_skills`. Validate: catalog
   listed, no `SKILL.md` body in the messages array.
5. **Skill activation** - `activate_skill(name)` returns the full body plus
   base path and bundled files; `run_skill_script(name, args)` runs the
   skill's `script.sh` with Git Bash in the code directory. Validate: an
   orientation request activates `launch-work-item` and runs its script.
6. **Assemble** - final system prompt: role, repo anchoring, capability
   rules, the skill catalog (names + descriptions only), and
   `config-service/AGENTS.md`. Validate the combined task from STEPS.md.
7. **Robustness** - clear failures for missing `mcp.json`, a server that
   will not start, unknown skill names, a missing or rejected
   `GEMINI_API_KEY`, an unknown model; retries for overload (503) and rate
   limits (429);
   tool output capped so one script cannot flood the context. Validate by
   breaking each on purpose.

## Windows specifics to design in, not discover later

- `subprocess.run(["bash", ...])` on Windows searches System32 before
  `PATH` and finds WSL's `bash.exe`, not Git Bash. Resolve bash explicitly:
  `PAIR_AGENT_BASH`, else the first `bash` on `PATH` outside
  `System32`/`WindowsApps`, else Git's default install path; fail clearly if
  none.
- Decode subprocess output as UTF-8 with replacement.

## Not doing (DESIGN.md non-goals, plus scope)

Tracing, evals, compaction or summarisation (the array grows for the
session; `/reset` starts over), background execution, multi-provider
support, write tools. The agent can read the repo and run the two
read-only Module 4 skills; it cannot edit files or commit.
