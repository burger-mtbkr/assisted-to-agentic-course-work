# Module 5: Tool Calling and MCP

> Tools sit between skills and the wider world — MCP is how your assistant reaches for them.

## Overview

This module is the second stop on the **agent-enablement continuum**: context → AGENTS.md → skills (M4) → **tools (M5)** → PAIR Agent (M6). Where Module 4 was about the *ergonomics* of working with the codebase via skills, Module 5 is about extending what the assistant can *reach for* — moving from a reader into an actor. We work through MCP fundamentals, build a real MCP server, and configure it in your coding agent.

The cohort builds a **Domain Language MCP** (`domain-lang-mcp`) — a stdio MCP server that wraps a provided `knowledge-graph` CLI to expose authoritative information about the `config-service` domain. The headline insight is that **MCP is a standardised interface** for tool extension, not a rewrite of the underlying services. You wrap what you already have (CLIs, REST APIs, DBs) so the agent can discover and reach for it, and you keep the abstraction stable so the backend can change without the agent's call site changing.

## Learning Objectives

By the end of this module, participants will:

1. Locate tools on the agent-enablement continuum and articulate where MCP fits among other tool-calling options.
2. Explain the MCP architecture: host, client, server, tool; the JSON-RPC handshake; capability negotiation.
3. Distinguish server capabilities (tools, prompts, resources) from client capabilities (elicitation, sampling, roots) and say what each is for.
4. Choose between stdio and HTTP transports based on deployment characteristics — and know SSE is deprecated.
5. Design MCP tools that an LLM can use well: verb-noun naming, specific descriptions, well-typed input schemas, appropriate granularity, predictable error categories.
6. Build a working stdio MCP server that wraps an existing CLI, validated with MCP Inspector and integrated into their coding agent.
7. Recognise common MCP security concerns: prompt injection via tool output, tool poisoning via metadata changes, lack-of-oversight risks of broad permissions.
8. Have at least one working MCP server (`domain-lang-mcp`) configured in their harness that their PAIR Agent will use in Module 6.

## Module Structure

The lecture is a 16-section arc grouped into six clusters. Demo lands in section 15, exercise framing in section 16.

### 1. Where we are (Sections 1–2)

- **Journey checkpoint**: M1 collaboration, M2 the WHAT (semantic context), M3 the HOW (procedural context), M4 zoomed-in process via skills, **M5 tools — extending what your assistant can reach for**, M6 preview (the PAIR Agent that uses your skills + tools).
- **Learning objectives**: goal, takeaway, hope.

### 2. What is MCP and why (Sections 3–7)

- **Tool-calling options**: direct CLI access, code-mode capabilities, MCP, sub-agents-as-tools.
- **Why MCP**: standardised, discoverable, scoped, context-aware, AI-native.
- **MCP vs direct CLI access — the fair pushback**: the "but couldn't we just give the agent the CLI?" question. Answer: stability, sharability, decoupling, scoping — worked example using `domain-lang-mcp`.
- **Components & protocol**: host / client / server / tool; JSON-RPC over a stateful connection.
- **Capabilities**: server (tools, prompts, resources) and client (elicitation, sampling, roots).

### 3. Server architecture (Sections 8–10)

- **Transport options**: stdio (local, single-client) vs Streamable HTTP (multi-client, remote). SSE deprecated.
- **Initialisation & lifecycle**: handshake, capability negotiation, ready, shutdown.
- **Wrap, don't rewrite**: the common misconception; the server is a bridge to existing services.

### 4. Tool design (Sections 11–13)

- **Anatomy of a tool**: name, description (read by the LLM), input schema; the tool handler lifecycle.
- **Naming, descriptions, schemas, granularity**: verb-noun pattern, specific verb+situation in descriptions, JSON Schema validation features, fine-grained beats coarse-grained.
- **Error handling & testing**: protocol vs validation vs service errors; MCP Inspector + in-memory SDK Client.

### 5. Security & ecosystem (Section 14)

- **Security & deployment**: prompt injection, tool poisoning, oversight risks; where MCPs run (uv/npm/Docker/marketplaces).

### 6. Demo and exercise (Sections 15–16)

- **Demo**: live `domain-lang-mcp` build — show the CLI, start stdio server in Inspector, debug a failure, register in the harness, use via natural language.
- **Exercise + PAIR Agent connection**: cohort builds their own stdio MCP server; what they build today their PAIR Agent uses in M6.

## Implementation Notes

### Materials

- Slide deck (`slides/slides.md`, MARP) — 16-section arc
- MCP server design template: `deliverables/examples/MCP_SERVER_DESIGN_TEMPLATE.md`
- Worked design doc: `deliverables/examples/domain-lang-mcp-DESIGN.md`
- Provided knowledge-graph backend: `deliverables/examples/knowledge-graph/` (YAML + CLI + REST API + SQLite store)
- Reference MCP servers: `deliverables/examples/domain-lang-mcp/` (stdio + HTTP variants)
- Configuration API continuity copy: `deliverables/examples/config-service/`
- Exercise instructions: `deliverables/project/INSTRUCTIONS.md`
- Reflection prompts: `deliverables/project/INTEGRATE.md`

### Demo Environment

- A coding agent that supports MCP (Claude Code, Cline, Codex CLI, Goose, OpenCode)
- `uv` installed
- MCP Inspector available via `npx @modelcontextprotocol/inspector`
- Terminal in `deliverables/examples/domain-lang-mcp/`
- `knowledge.db` built (run `uv run knowledge-graph import` from `deliverables/examples/knowledge-graph/`)

### Key Outcomes

- A working stdio MCP server, designed and authored in the cohort session, in the language of their choice
- A filled-in MCP server design doc that can be referenced when authoring future servers
- Practical familiarity with MCP Inspector — the debug seam between authoring and the harness
- An MCP server registered and invoked from their coding agent — the configuration experience as well as the building experience
- A server that becomes part of the participant's PAIR Agent repertoire in Module 6

### Further Resources

- MCP specification: https://spec.modelcontextprotocol.io
- MCP Inspector: https://github.com/modelcontextprotocol/inspector
- Python MCP SDK: https://github.com/modelcontextprotocol/python-sdk
- TypeScript MCP SDK: https://github.com/modelcontextprotocol/typescript-sdk
- Community SDKs (Go, Rust, Java, etc.): https://github.com/modelcontextprotocol
- Anthropic's MCP examples: https://github.com/modelcontextprotocol/servers
