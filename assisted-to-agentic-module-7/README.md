# Module 7: Conversation and Tool Calling

> Building the first specialist in an agent team: the Doctor

## Overview

Module 7 begins Phase 3 by moving from a hand-rolled agent loop to a framework-based agent.

In Module 6, students built the core mechanics themselves: conversation, messages, tool calls, skills, and the loop that connects them. In Module 7, those concepts carry forward into a framework-based implementation. This gives students a clearer view of what the framework handles, what the developer still owns, and how to design an agent with a focused responsibility.

The running example is the **Doctor**: a diagnostic agent for codebase health. The Doctor can converse with a human, run deterministic checks, inspect files, use a diagnostic skill, and produce an evidence-based health report.

The Doctor is the implementation vehicle. The core concepts are conversation, scoped identity, tool calling, deterministic sensors, reusable process, and evidence-based reporting.

## Phase 3 Capability Progression

Phase 3 evolves one useful specialist into a small, human-orchestrated agent team.

| Module | Specialist | Main capability focus |
| --- | --- | --- |
| 7 | Doctor | Conversation and tool use |
| 8 | Librarian | Memory, knowledge, and retrieval |
| 9 | Mechanic + integration | Handoff, verification, and coordination |

Across Phase 3, students will build toward six capability layers:

1. **Conversation** — the agent can interact with a human through a stable identity and task frame.
2. **Tool use / action** — the agent can choose and call tools through bounded interfaces.
3. **Memory** — the agent can preserve useful working or durable state across interactions.
4. **Knowledge / retrieval** — the agent can find relevant code, docs, decisions, and relationships.
5. **Reasoning / verification** — the agent can use staged model calls to reason and check work.
6. **Coordination** — multiple specialists can collaborate through explicit handoff artifacts.

Module 7 focuses on the first two layers: conversation and tool use.

## Learning Objectives

By the end of this module, participants will:

1. Explain how a framework-based agent differs from the hand-rolled agent loop built in Module 6.
2. Design a focused agent identity with clear responsibility boundaries.
3. Build a conversational agent using an agentic SDK (e.g. LangChain Deep Agents).
4. Expose a small deterministic tool set to an agent.
5. Use tool calls as grounded sensors for diagnosis.
6. Add an Agent Skill as reusable diagnostic process.
7. Produce an evidence-based health report from tool results.
8. Inspect lightweight conversation logs and filesystem traces.

## Module Structure

### 1. Phase 3 Orientation

- From one useful specialist to a small agent team
- Doctor, Librarian, and Mechanic roles
- Six capability layers across Phase 3
- Why Phase 3 starts with one focused specialist

### 2. From Hand-Rolled Loop to Framework Agent

- What Module 6 made explicit
- What an agent framework provides
- What the developer still designs:
  - identity
  - scope
  - tools
  - process
  - evidence standards

### 3. Conversation and Scoped Identity

- System prompt as identity and boundary
- Conversation as state and turn-taking
- The Doctor as a focused diagnostic role
- Responsibility boundaries as part of agent design

### 4. Tool Calling

- Tool calling as model-selected action
- Tool schemas as contracts
- Small tool surfaces
- Deterministic tools as sensors
- Doctor tools and capabilities:
  - built-in filesystem tools: `ls`, `read_file`, `glob`, `grep`
  - custom command tools: `run_tests`, `run_lint`

### 5. Skills as Reusable Process

- Agent Skills as procedural guidance
- The `triage-codebase-health` skill
- Progressive disclosure: metadata first, full `SKILL.md` when needed
- What to run first
- What evidence is sufficient
- How to structure a health report

### 6. Lightweight Inspectability

- Conversation persistence to files
- Filesystem trace output
- Streaming model output and tool progress
- Inspecting what the agent did and why

### 7. Hands-on Exercise: Build the Doctor

Participants build a focused diagnostic agent that can:

- converse with the user
- run tests and lint
- inspect files when evidence points to them
- apply a diagnostic skill
- produce a structured health report
- save conversation and trace artifacts

## Implementation Notes

### Materials

- Slide deck: `slides.pdf`
- Example implementation: `deliverables/examples/doctor/`
- Exercise materials: `deliverables/project/`

### Example Stack

The reference implementation uses:

- Python
- LangChain Deep Agents
- Agent Skills
- local filesystem conversation logs
- lightweight JSONL trace output
- `config-service` as the diagnosis target

Deep Agents is a means to an end. The module is about the agent design concepts, not about Python, LangChain, or the Doctor scenario specifically.

## Key Outcomes

By the end of Module 7, students should have:

- a working framework-based diagnostic agent
- a clear mental model of conversation and tool calling
- experience designing a small, bounded tool surface
- a reusable diagnostic skill
- an evidence-based health report produced by the agent
- local conversation and trace artifacts they can inspect
