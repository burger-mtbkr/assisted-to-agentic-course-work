# Module 6: Building the PAIR Agent

> From skills and tools to harness — build the bespoke agent that uses them.

## Overview

Module 6 is the capstone of Phase 2. In Module 4 students taught their assistant a process through a skill. In Module 5 they built an MCP server that extended what the assistant could reach for. In Module 6 they assemble those pieces into a **PAIR Agent**: a bespoke, repo-anchored harness around the `config-service` codebase.

This module is intentionally narrow. Students are not building a production agent framework. They are building just enough harness to see the moving parts clearly:

- a conversation loop
- a `messages` array as working memory
- a harness-owned tool registry
- MCP tool discovery from `mcp.json`
- skill discovery and progressive disclosure through `activate_skill(name)`

This is the moment where Phase 2 flips perspective. In Module 5 students built the **server side** of tool calling. In Module 6 they build the **client/harness side** that discovers and invokes those tools.

## Learning Objectives

By the end of this module, participants will:

1. Explain what an agent harness is and identify its minimal moving parts.
2. Use a `messages` array as the agent's working memory and understand how it functions as an in-session context window.
3. Build a simple conversational loop that can alternate between model responses and tool calls.
4. Distinguish between harness-owned tools and MCP-discovered tools.
5. Implement skills support using progressive disclosure: catalog first, then full `SKILL.md` only when activated.
6. Load MCP server definitions from `mcp.json`, discover tools, and invoke them from the harness.
7. Assemble a repo-specific PAIR Agent around `config-service` that can use the skill from Module 4 and the MCP server from Module 5.

## Module Structure

The lecture is a 15-section arc grouped into five clusters.

### 1. Where we are (Sections 1–2)

- **Journey checkpoint**: M1 collaboration foundations, M2 semantic context, M3 procedural workflow, M4 skills, M5 MCP tools, M6 bespoke harness.
- **Goal of the day**: stop borrowing a generic coding agent and build the harness that powers one.

### 2. The core harness (Sections 3–6)

- **What an agent harness is**: the smallest loop that can converse, decide, act, and continue.
- **The messages array**: the core state model; the most important new concept in the module.
- **The conversation loop**: prompt, respond, inspect tool calls, execute, continue.
- **Provider seam**: implement one tool-calling-capable provider correctly; keep secrets configurable and out of source control.

### 3. Capabilities and disclosure (Sections 7–10)

- **Harness-owned tools**: tools the harness itself provides, including `list_skills` and `activate_skill`.
- **MCP-discovered tools**: tools loaded from `mcp.json` via an MCP client library.
- **Progressive disclosure as a harness pattern**: skills and MCP tools both advertise lightweight metadata up front and defer heavy content or results until invocation.
- **Skill activation**: the model sees the skill catalog, then calls `activate_skill(name)` only when it needs the full instructions.

### 4. The PAIR Agent assembly (Sections 11–13)

- **Repo anchoring**: why the harness lives beside `config-service` in this phase.
- **M4 + M5 + M6 connection**: skill + MCP + harness.
- **Manual verification mindset**: don't just run tests; chat with the agent and watch it reach for its capabilities.

### 5. Demo and exercise (Sections 14–15)

- **Demo**: assemble a minimal PAIR Agent in front of the cohort and show it using both harness-owned and MCP-provided capabilities.
- **Exercise**: build the bespoke harness yourself, in the language of your choice, against the `config-service` codebase you've been carrying through Phase 2.

## Implementation Notes

### Materials

- Slide deck: `slides/slides.md`
- Demo runbook: `DEMO.md`
- Example implementation: `deliverables/examples/pair-agent/` (to be refreshed)
- Exercise materials:
  - `deliverables/project/DESIGN.md`
  - `deliverables/project/STEPS.md`
  - `deliverables/project/EXERCISE.md`

### Exercise constraints

- The example implementation may be opinionated; the student exercise must remain language-agnostic.
- Students only need to support **one** tool-calling-capable model/provider path.
- Students should use an MCP client library for their language rather than implementing the MCP protocol from scratch.
- `mcp.json` is the only MCP configuration file taught in this module.

### Out of scope

These topics are deliberately deferred to Module 7 and beyond:

- tracing and observability frameworks
- formal evaluation harnesses
- advanced context compaction or summarisation
- autonomous background sessions
- multi-provider abstraction as a course requirement

## Key Outcomes

- A working mental model of an agent harness.
- Direct experience with the `messages` array as working memory.
- A bespoke PAIR Agent that can converse, discover MCP tools, and activate skills progressively.
- A concrete bridge from the artifacts students built in Modules 4 and 5 into the harness and framework topics of Module 7.

## Further Resources

- Agent Skills overview: https://agentskills.io/
- Agent Skills specification: https://agentskills.io/specification
- Adding skills support to an agent: https://agentskills.io/client-implementation/adding-skills-support
- Optimizing skill descriptions: https://agentskills.io/skill-creation/optimizing-descriptions
- Equipping agents for the real world with Agent Skills: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills?_bhlid=fb54f3ffd4d8cdcde5a43e105d8980dbb53abb65
- Claude Code MCP docs: https://docs.anthropic.com/en/docs/claude-code/mcp
- Official MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
