# knowledge/

The domain language of this service as a small graph: what each term means
here, which files implement it, what to watch out for, and how terms relate.
It is the data behind the `domain-lang` MCP server
(`../../domain-lang-mcp/`), which lets an agent ask "what does
ConfigurationItem mean in this system?" and get this repo's answer rather
than a generic one.

```text
nodes/config_service.yaml   Application, ConfigurationItem, ScanCache,
                            ErrorResponse, HealthStatus, AdminUI
nodes/feature_flags.yaml    FeatureFlag, FlagKey, FlagConsumptionPattern
edges/config_service.yaml   directed relationships between them
knowledge.db                built from the YAML, git-ignored
```

The YAML schema is the curriculum `knowledge-graph` CLI's (Module 5,
`modules/assisted-to-agentic-module-5/examples/knowledge-graph/README.md`).

## Keep it in step with the code

When a change renames, moves, or redefines something a node describes,
update the node in the same commit - `source_files` paths are what the agent
will open. Then rebuild and check the db, from the CLI's directory:

```bash
cd modules/assisted-to-agentic-module-5/examples/knowledge-graph
uv run knowledge-graph import --knowledge-dir ../../../../config-service/knowledge \
  --db ../../../../config-service/knowledge/knowledge.db
uv run knowledge-graph validate --db ../../../../config-service/knowledge/knowledge.db
```

The MCP server reports a missing `knowledge.db` as an error rather than
answering `not_found` for everything, but it cannot tell when the db is
older than the YAML - re-import after every edit.
