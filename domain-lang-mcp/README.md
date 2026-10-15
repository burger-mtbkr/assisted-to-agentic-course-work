# domain-lang-mcp

Stdio MCP server that gives an agent authoritative answers about
`config-service`'s domain language. Built in Module 5, consumed by the
Module 6 PAIR Agent (`../pair-agent/`), registered for Claude Code in the
repo's `.mcp.json`.

It wraps the curriculum's `knowledge-graph` CLI by subprocess and points it
at this repo's own graph in `../config-service/knowledge/`. Design and
decisions: `DESIGN.md`. Build order: `IMPLEMENTATION_PLAN.md`.

| Tool | Answers |
|---|---|
| `ping` | Is this server reachable? |
| `lookup_term` | What does this term mean here, where is it implemented, what to watch out for? |
| `get_related_terms` | What does this term connect to (or get confused with)? |
| `list_domain_areas` | Which parts of the domain exist? |
| `validate_knowledge_graph` | Is the graph internally consistent? |

## Configuration

| Variable | Required | Meaning |
|---|---|---|
| `KG_PROJECT_DIR` | yes | The knowledge-graph CLI project (`modules/assisted-to-agentic-module-5/examples/knowledge-graph`) |
| `KG_DB` | yes | The SQLite db built from `config-service/knowledge/` (`config-service/knowledge/knowledge.db`). Required because the CLI silently creates an empty db when pointed at a missing one |
| `KG_TIMEOUT_SECONDS` | no | Per-call CLI timeout, default 60 |

Relative paths resolve against the server's working directory - the repo
root when launched from `.mcp.json`.

## Setup

Needs the Module 5 curriculum zip extracted (the CLI lives in git-ignored
`modules/.../examples/`) and the db built - see
`../config-service/knowledge/README.md`.

## Running and testing

From the repo root:

```bash
uv run --project domain-lang-mcp pytest domain-lang-mcp    # 30 tests
npx @modelcontextprotocol/inspector \
  -e KG_PROJECT_DIR=modules/assisted-to-agentic-module-5/examples/knowledge-graph \
  -e KG_DB=config-service/knowledge/knowledge.db \
  uv run --quiet --project domain-lang-mcp domain-lang-mcp
```

The integration tests import the YAML into a temporary db, so they never
touch `knowledge.db`; they skip when the curriculum CLI is absent.

## Errors

Unknown terms return `{"error": "not_found", "term": ...}` as a normal
result. Anything that stops the graph answering returns `isError: true` with
`{"error": "service_error", "reason", "detail", "fix"}` - reasons:
`not_configured`, `backend_unreachable`, `knowledge_db_missing`,
`cli_failed`, `malformed_output`, `timeout`.
