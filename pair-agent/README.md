# pair-agent

The Module 6 PAIR Agent: a small, legible agent harness anchored to
`config-service`. It converses, keeps a `messages` array as working memory,
runs a tool loop, discovers the Module 5 `domain-lang` MCP server from
`mcp.json`, and discovers this repo's Module 4 skills, loading each one in
full only when it is activated.

Plan and decisions: `IMPLEMENTATION_PLAN.md`. Assignment:
`modules/assisted-to-agentic-module-6/project/DESIGN.md`.

## Run it

From the repo root:

```bash
uv run --project pair-agent pair-agent
```

Needs a Google Gemini API key: copy `.env.example` to `.env` (git-ignored)
and set `GEMINI_API_KEY`. It also needs what the MCP server needs (the
Module 5 curriculum zip extracted and `config-service/knowledge/knowledge.db`
built - see `config-service/knowledge/README.md`). The key is never
committed.

In the session, type a message, or one of:

| Command | Does |
|---|---|
| `/tools` | list every registered tool and where it came from (`harness` / `mcp:<server>`) |
| `/messages` | print the messages array - the agent's working memory |
| `/save PATH` / `/load PATH` | persist / restore a conversation as JSON |
| `/reset` | clear everything but the system prompt |
| `/quit` | exit and print the session's token usage |

Tool calls are printed as they happen (`-> name(args)`, `<- name: ok, N chars`).

## Settings

| Variable | Default |
|---|---|
| `GEMINI_API_KEY` | required - from Google AI Studio, kept in `.env` |
| `GEMINI_MODEL` | `gemini-flash-latest` - the free-tier Flash model |
| `PAIR_AGENT_CODE_DIR` | `../config-service` - what the repo tools read and skill scripts run in |
| `PAIR_AGENT_SKILLS_DIR` | `../.claude/skills` - the same skills Claude Code uses |
| `PAIR_AGENT_MCP_CONFIG` | `./mcp.json` |
| `PAIR_AGENT_MAX_TOOL_ROUNDS` | `12` - then the model must answer with what it has |
| `PAIR_AGENT_BASH` | auto: Git Bash, never WSL's `System32\bash.exe` |

The provider is Gemini through Google's OpenAI-compatible chat endpoint,
with no SDK - one small module (`provider.py`). Gemini attaches a "thought
signature" to each tool call that must be sent back with that call on the
next request; the provider keeps it with the call in the messages array.
Free-tier use costs nothing as long as the key's Google project has no
billing account attached; the free tier has per-minute and per-day limits,
and overload (503) and rate-limit (429) replies are retried.

## Tools

| Tool | Source | Purpose |
|---|---|---|
| `read_file`, `search_code` | harness | read-only access to the code directory (confined to it; `git grep`) |
| `list_skills` | harness | skill names, descriptions, locations (no bodies) |
| `activate_skill` | harness | load a skill's full `SKILL.md`, base directory, bundled files |
| `run_skill_script` | harness | run an activated skill's `script.sh` in the code directory |
| `mcp__domain-lang__*` | MCP | the five Module 5 tools, discovered at startup |

The harness cannot write files or commit. The only commands it runs are the
skills' own scripts - and `land-work-item`'s runs the project's real quality
gate (`npm run check`: tests, build, lint), so it is not side-effect free.
Script arguments are checked: `--project-dir` is refused and any path must
resolve inside the code directory. `read_file` refuses git-ignored files
(`config-service/.env` holds secrets), and `run_skill_script` works only
for a skill activated earlier in the session.

## Tests

```bash
uv run --project pair-agent pytest pair-agent
```

The MCP integration test starts the real `domain-lang` server from
`mcp.json`, and skips if `knowledge.db` has not been built. The model is
never called by tests; the six manual validation flows from `STEPS.md` were
run against Gemini Flash (see the Module 6 journal).
