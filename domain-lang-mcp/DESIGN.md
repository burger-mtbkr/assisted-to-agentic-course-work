# domain-lang-mcp - Design Doc

Module 5's `MCP_SERVER_DESIGN_TEMPLATE.md`, filled in before the server was
written. Built against this repo's `config-service` (C#/.NET, DynamoDB), not
the curriculum's Python example service.

---

## Server identity

**Server name:** `domain-lang` (package `domain-lang-mcp`)

**One-line purpose:** Give an agent authoritative answers about
`config-service`'s domain language - what a term means here, which C# files
implement it, what to watch out for, and how it relates to other terms - so
it stops guessing from generic knowledge of "config services" and "feature
flags".

**Underlying backend:** The curriculum's `knowledge-graph` CLI (Typer +
SQLite), invoked as a subprocess. The *data* is repo-owned:
`config-service/knowledge/{nodes,edges}/*.yaml`, imported into
`config-service/knowledge/knowledge.db`. The CLI is the curriculum's; the
facts are ours.

**Transport:** stdio. One developer, one local harness at a time, data on
the same disk - no reason to pay for HTTP's server lifecycle, ports, or auth.

### Why repo-owned YAML instead of the provided `knowledge/`

The provided YAML describes the curriculum's Python service: `svc/api/*.py`
source paths, an `Environment` concept, JSON `Schema`s, a `FlagScope`. None
of those exist here - this service has no environments, no schemas, and
boolean-only flags. An MCP whose whole value is "authoritative" would be
confidently pointing the agent at files that do not exist. The Module 6
curriculum drop rewrites its own `ConfigurationItem` node for exactly this
reason (its definition now says "domain language, not a concrete Python
type"). Same fix, applied to our repo: keep the node **ids** the exercise
verifies against (`configuration_item`, `feature_flag`, areas
`config_service` / `feature_flags`) and replace the contents with facts from
`context/`, `README.md`, and the C# source.

---

## Tools

All five are read-only (`readOnlyHint: true`).

### Tool: `ping`

**Description:** Connectivity check for this MCP server only. Echoes the
message back as "Pong: <message>". Use it to confirm the domain-lang server
is reachable before relying on its other tools; it does not touch the
knowledge graph, so a successful ping says nothing about whether the graph
is loaded - use `validate_knowledge_graph` for that.

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | yes | Text to echo back |

**Output:** Plain text `Pong: <message>`.

**Errors handled:** Missing `message` - schema rejection.

### Tool: `lookup_term`

**Description:** Look up what a domain term means in the config-service
codebase: its definition, aliases, warnings, the source files that implement
it, and the docs that describe it. Accepts the term's id
(`configuration_item`), display name (`ConfigurationItem`), or an alias
(`config entry`, `flag`), case-insensitive. Use this whenever the user names
a domain concept - Application, ConfigurationItem, FeatureFlag, FlagKey,
ScanCache, ErrorResponse - before searching code or answering from general
knowledge, because this repo's meaning and file names differ from common
conventions. Returns `{"error": "not_found"}` for unknown terms.

| Field | Type | Required | Description |
|---|---|---|---|
| `term` | string | yes | Id, name, or alias; 1-200 chars, not blank |

**Output:** JSON object `{id, type, area, name, definition, aliases,
warnings, source_files, documentation}`. On a miss:
`{"error": "not_found", "term": "<input>"}`.

**Errors handled:**
- Unknown term -> `{"error": "not_found", "term": ...}`, *not* flagged as a
  tool error: it is a clean negative answer the agent should act on.
- Blank / missing term -> schema rejection before the handler runs.
- Backend problems -> `service_error` (see the error table).

### Tool: `get_related_terms`

**Description:** List the outgoing relationships of a domain term in the
config-service knowledge graph, as `{from, to, relationship}` records - e.g.
FeatureFlag `scoped_to` Application, `consumed_via` FlagConsumptionPattern.
Use this after `lookup_term` when you need adjacent concepts: what else a
change will touch, or which terms are easily confused with this one
(`not_equivalent_to`). Edges are directed; only edges *from* the term are
returned.

| Field | Type | Required | Description |
|---|---|---|---|
| `term` | string | yes | Id, name, or alias; 1-200 chars, not blank |

**Output:** JSON array of `{from, to, relationship}`; `[]` when the term
exists but has no outgoing edges. On a miss: `{"error": "not_found", ...}`.

**Errors handled:** Same as `lookup_term`.

### Tool: `list_domain_areas`

**Description:** List the domain areas the knowledge graph is partitioned
into (currently `config_service` and `feature_flags`). Use for orientation
when you do not yet know which part of the domain a question belongs to. No
input.

**Output:** JSON array of area strings.

**Errors handled:** Backend problems -> `service_error`.

### Tool: `validate_knowledge_graph`

**Description:** Check the knowledge graph for integrity problems - edges
that reference terms which do not exist. Returns `{"valid": bool,
"issues": [...]}`. Use after the YAML in `config-service/knowledge/` has
been edited and re-imported, or when other tools return surprising
not_found results. No input.

**Output:** `{"valid": true, "issues": []}` or `{"valid": false, "issues":
["edge references missing to_node ...", ...]}`.

**Errors handled:** A CLI crash (exit code other than 0 or 1) is a
`service_error`, *not* reported as validation issues.

---

## Granularity check

- `lookup_term` vs `get_related_terms`: kept separate. "What is X" and "what
  does X connect to" are different questions, and two narrow tools with
  distinct descriptions are picked more reliably than one tool with an
  `include_edges` flag.
- `list_domain_areas` vs `validate_knowledge_graph`: both take no input,
  but one is orientation and the other is integrity. Separate.
- No `search_terms`: the graph is 9 nodes and alias matching covers
  discovery. Revisit if it grows past what an agent can enumerate.

---

## Error categories you'll handle

| Category | Example in this server | How you'll signal it |
|---|---|---|
| Validation | Missing or blank `term` | Schema rejection (`minLength`, non-blank `pattern`) before the handler runs |
| Not found | Term not in the graph | `{"error": "not_found", "term": ...}`, `isError: false` |
| Service | Backend unreachable, missing db, CLI crash, non-JSON output, timeout | `{"error": "service_error", "reason": ..., "detail": ..., "fix": ...}`, `isError: true` |

Service `reason` values: `not_configured` (`KG_PROJECT_DIR` or `KG_DB`
unset),
`backend_unreachable` (directory or `uv` missing), `knowledge_db_missing`,
`cli_failed`, `malformed_output`, `timeout`. Every one carries a `fix`
sentence the agent can relay instead of a stack trace.

Three failure modes found by running the CLI before designing around it,
and designed out here:

- **A missing `--db` is silent.** The CLI creates an empty database on the
  spot, so every lookup returns `not_found` and `validate` reports "valid".
  The server requires `KG_DB` and checks the file exists *before* calling
  the CLI, returning `not_configured` / `knowledge_db_missing` with the
  import command.
- **Windows console encoding.** With output piped, Python on Windows encodes
  stdout as cp1252 and the CLI crashes on any non-ASCII character. The
  server runs the CLI with `PYTHONIOENCODING=utf-8` and decodes as UTF-8.
- **Terms that look like options.** A term such as `--help` would be parsed
  as a CLI flag. The server passes options first and the term after `--`.

---

## Testing plan

- Unit tests for the subprocess wrapper's error mapping with an injected
  runner (exit codes, bad JSON, missing directory, missing db, timeout).
- In-memory MCP `Client` integration tests against the real CLI and the
  real repo-owned graph: tool list, every tool's happy path, not_found,
  schema rejection, bad `KG_PROJECT_DIR`, missing db, option-like term.
- MCP Inspector (CLI mode) against the stdio entry point: `tools/list` and
  each verification call from the exercise.
- End to end from Claude Code with natural-language prompts ("What does
  ConfigurationItem mean in this system?", "What's related to
  FeatureFlag?") and a check that the tool was actually called.

---

## Configuration in your harness

- Harness: Claude Code, **project scope** - a `.mcp.json` committed at the
  repo root, so anyone who clones the course repo gets the server. Also the
  Module 6 PAIR Agent via `pair-agent/mcp.json`.
- Registration (equivalent to what `.mcp.json` contains):
  ```bash
  claude mcp add --scope project --transport stdio domain-lang \
    --env KG_PROJECT_DIR=modules/assisted-to-agentic-module-5/examples/knowledge-graph \
    --env KG_DB=config-service/knowledge/knowledge.db \
    -- uv run --project domain-lang-mcp domain-lang-mcp
  ```

---

## Open questions

- **Personal tool or team asset?** Team asset: the YAML lives in
  `config-service/` next to the code it describes so a change that renames
  `FlagService` can update the graph in the same commit. The server is
  registered at project scope for the same reason.
- **Who re-imports after YAML edits?** For now, a documented manual step;
  the server reports `knowledge_db_missing` rather than auto-importing,
  because a tool that silently rewrites a database on a read is surprising.
  A stale-but-present db is not detected - worth a checksum later if the
  graph changes often.
- **The CLI lives in git-ignored curriculum material.** A fresh clone needs
  the Module 5 zip extracted before the server works; the
  `backend_unreachable` error says so.
