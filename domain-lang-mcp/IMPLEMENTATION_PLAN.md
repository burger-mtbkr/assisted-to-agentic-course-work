# domain-lang-mcp - Implementation Plan

Covers exercise phases 1-4 (scaffold, `ping`, the subprocess wrapper plus
`lookup_term`, the remaining tools). `DESIGN.md` holds the *what*; this is
the *how* and the order.

## Stack

- Python 3.13+, `uv`, official MCP Python SDK (`mcp` 2.x - `MCPServer`;
  the 1.x `FastMCP` name no longer exists)
- `pytest` + `pytest-asyncio` for tests, as a dev dependency group only

## Layout

```text
domain-lang-mcp/
  pyproject.toml          # script entry point: domain-lang-mcp
  src/domain_lang_mcp/
    kg.py                 # subprocess wrapper + error mapping (no MCP imports)
    server.py             # MCP tool registration + stdio entry point
  tests/
    kg_test.py            # wrapper unit tests, injected fake runner
    server_test.py        # in-memory MCP Client against the real CLI + graph
```

The wrapper knows nothing about MCP and the server knows nothing about
subprocesses, so the error mapping can be tested without a protocol and the
protocol without a fake.

## Phase 1 - scaffold

1. `pyproject.toml` with `mcp` as the only runtime dependency.
2. `server.py`: `build_server()` returning an `MCPServer("domain-lang")`
   with no tools, and `main()` running it over stdio.
3. Verify: Inspector CLI `tools/list` returns an empty list.

## Phase 2 - `ping`

1. Register `ping(message: str)` returning `Pong: <message>`.
2. Verify: listed; `hello` -> `Pong: hello`; no `message` -> schema error.

## Phase 3 - wrapper + `lookup_term`

`kg.py`:

- `KgSettings.from_env()` - reads `KG_PROJECT_DIR` (required), `KG_DB`
  (required), `KG_TIMEOUT_SECONDS` (default 60; the first `uv run` may need
  to sync the CLI's environment). Relative paths resolve against the server
  process's working directory.
- `run_cli(settings, *args) -> CliResult(returncode, stdout, stderr)` - the
  reusable runner. `uv run knowledge-graph <args>`, cwd = `KG_PROJECT_DIR`,
  `PYTHONIOENCODING=utf-8`, timeout. Raises `KgServiceError(reason, detail,
  fix)` for: directory missing / `uv` missing (`backend_unreachable`),
  timeout.
- Pre-flight: `KG_PROJECT_DIR` or `KG_DB` unset -> `not_configured`; `KG_DB`
  file missing -> `knowledge_db_missing` (the CLI would otherwise create an
  empty db and answer `not_found` for everything).
- `query_json(settings, command, *args)` - builds
  `<command> --format json [--db X] -- <args>`, accepts exit 0 or exit 1
  *only* when stdout is the CLI's `not_found` payload; anything else is
  `cli_failed` (with the stderr tail) or `malformed_output`.

`server.py`:

- `lookup_term(term)` with `term` constrained to 1-200 chars and not blank.
- Service errors returned as `CallToolResult(is_error=True)` whose text is
  the JSON error object; `not_found` returned as a normal result.

Verify (Inspector + tests): `ConfigurationItem` -> node record;
`nonsense` -> `{"error": "not_found", "term": "nonsense"}`; no term ->
schema error; `KG_PROJECT_DIR` pointing nowhere -> `backend_unreachable`
with a fix, not a traceback.

## Phase 4 - remaining tools

All three, not two: `get_related_terms` reuses `query_json`;
`list_domain_areas` likewise with no args; `validate_knowledge_graph` uses
`run_cli` directly because `validate` has no `--format`. Exit 0 -> valid,
exit 1 -> issues from stdout lines, anything else -> `cli_failed`.

Verify: `feature_flag` has >= 3 edges; areas are
`["config_service", "feature_flags"]`; validate returns
`{"valid": true, "issues": []}`.

## Phase 5 - registration (after Inspector passes)

- Project-scope `.mcp.json` at the repo root.
- Headless Claude Code run with each verification prompt, checking the
  stream for an actual `mcp__domain-lang__lookup_term` /
  `get_related_terms` call rather than trusting the prose answer.

## Not doing

- Phase 6 (HTTP variant) - optional stretch; stdio is the right transport
  for a single-developer local graph (see `DESIGN.md`).
- Auto-import on startup or a staleness check (see `DESIGN.md` open
  questions).
