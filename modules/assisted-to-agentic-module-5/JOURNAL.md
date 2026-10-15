# Module 5 Journal

## Entry 1: Design, build, verify and register the `domain-lang` MCP server

- **Prompt**: "contiue with th emodules. you have done soemoalready do the
  next up to moduel 6", then mid-flight: "youll need to create a mcp
  somewhere in one of th emodukes too. do everything untilyou finish moduel
  6"
- **Tool**: Claude Code (VS Code extension)
- **Mode**: Direct execution, bypass permissions. Followed the exercise's
  own order instead of a plan-mode gate: design doc from the template ->
  `IMPLEMENTATION_PLAN.md` -> scaffold -> tools -> Inspector -> harness.
- **Context**: `modules/assisted-to-agentic-module-5/` (README,
  `project/INSTRUCTIONS.md`, `project/INTEGRATE.md`,
  `MCP_SERVER_DESIGN_TEMPLATE.md`, the worked `domain-lang-mcp-DESIGN.md`,
  the reference `domain-lang-mcp/` and the `knowledge-graph` backend), plus
  `config-service/` (`context/ABOUT.md`, `context/ARCHITECTURE.md`,
  `README.md`, `changes/001-feature-flags.md`, the C# models) as the source
  of the domain facts.
- **Model**: Claude Opus 5.5 (`claude-opus-5-5`)
- **Input**: Read the curriculum and ran the provided CLI before designing.
  Two findings shaped everything after:
  1. The provided YAML describes the curriculum's *Python* service
     (`svc/api/*.py`, Environments, Schemas, FlagScope), none of which exist
     in this repo's C#/.NET service. The Module 6 zip had already corrected
     its own `ConfigurationItem` node for the same reason. So I wrote
     repo-owned YAML in `config-service/knowledge/` and kept the node ids the
     exercise verifies against.
  2. The CLI fails silently or crashes in three ways: a missing `--db`
     creates an empty database, so everything is `not_found` and `validate`
     says "valid"; on Windows, piped output is cp1252, so a non-ASCII
     character crashes it; and a term like `--help` is parsed as a flag.
- **Output**:
  - `domain-lang-mcp/` at the repo root (it spans M5 and M6), Python 3.14 +
    `mcp` 2.3 `MCPServer`: `kg.py` (subprocess wrapper, no MCP imports) and
    `server.py` (five read-only tools). `DESIGN.md` (filled-in template),
    `IMPLEMENTATION_PLAN.md`, `README.md`.
  - Error contract: `not_found` is a normal result; backend problems return
    `isError: true` with `{error: service_error, reason, detail, fix}`
    across six reasons. Blank terms are rejected by the schema (`minLength`
    plus a non-blank `pattern`), not just missing ones.
  - `config-service/knowledge/` with 9 nodes and 14 edges. Every
    `source_files` path was checked to exist. The import and validate steps
    are documented in `knowledge/README.md`, and the built db is
    git-ignored.
  - A reviewer pass during Module 6 hardened three things: `KG_DB` is now
    required (left unset, the CLI silently opened an empty database); the CLI
    subprocess no longer inherits the server's stdin, which is the JSON-RPC
    pipe; and it is killed on cancellation as well as on timeout.
  - 30 tests: 15 for the wrapper with an injected runner, and 15 through
    the MCP protocol (in-memory `Client`) against the real CLI and a temp db
    imported from the repo YAML.
  - MCP Inspector (CLI mode) passed all nine exercise checks: `ping`, ping
    with no message, ConfigurationItem, nonsense, no term, bad
    `KG_PROJECT_DIR`, `feature_flag` edges (5), areas, and validate.
  - Registered at project scope (`.mcp.json`) and approved locally. Headless
    `claude -p` runs of both verification prompts called
    `mcp__domain-lang__lookup_term` and `get_related_terms` first, before
    any Glob/Read, and answered from the repo's own graph (`Configuration.cs`,
    "no per-environment values", the 404-vs-disabled warning).
- **Cost**: Two headless Claude Code verification runs, $0.26 + $0.22 as
  reported by `claude -p`. The main session is on a subscription with no
  per-call figure.
- **Reflections**: The most valuable hour was the one before writing any
  server code: running the backend by hand. The missing-db case in
  particular passes the reference server's tests and would show up as a
  confidently wrong agent ("that term does not exist"), not an error. The
  other two would surface only as unreadable tracebacks. The second lesson was that the
  exercise's own verification ("`ConfigurationItem` returns a node record")
  would have passed against data describing a different codebase. The data
  had to be checked against our code, not just the protocol against the
  spec. Phase 6 (HTTP) skipped deliberately: a single-developer local graph
  is exactly the case where stdio is right.
