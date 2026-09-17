# Module 9: Multi-Agent Coordination and Evaluation

> Coordinating specialist agents through explicit interfaces, handoff artifacts, human checkpoints, and verification loops.

## Overview

Module 9 completes the Phase 3 arc by adding the **Mechanic** to the Doctor and Librarian specialist pattern:

| Module | Specialist | Boundary |
| --- | --- | --- |
| 7 | Doctor | Diagnoses codebase health; read-only codebase access; deterministic checks as sensors |
| 8 | Librarian | Retrieves and records codebase knowledge; writes only to memory artifacts |
| 9 | Mechanic | Makes scoped code changes; submits work back to Doctor for verification |

The central lesson:

> Multi-agent systems become useful when specialists have clear responsibilities, common interfaces, explicit handoff contracts, and evaluation loops that catch coordination failures.

Students will design and implement a small codebase-maintenance workflow over `config-service`:

```text
Human request
  → Doctor diagnoses
  → Librarian retrieves context
  → Human approves repair boundary
  → Mechanic patches with a coding-agent harness
  → Doctor verifies
  → Librarian optionally records the repair narrative
```

The reference implementation uses **Pi coding agent** as the Mechanic. Pi is one replaceable coding-agent harness behind a common port. The same interface could wrap Claude Code, Codex, another coding-agent CLI, an SDK-backed agent, or a human-assisted patch process.

## Learning Objectives

By the end of this module, participants will be able to:

1. Explain when multi-agent coordination is justified and when it is unnecessary theatre.
2. Distinguish human-orchestrated, pipeline, supervisor/worker, peer-to-peer, fan-out/fan-in, and agents-as-tools coordination patterns.
3. Design a common interface for heterogeneous agents.
4. Create structured handoff artifacts that are small enough to pass and rich enough to act on.
5. Compose Doctor, Librarian, and Mechanic into a diagnosis → context → change → verification loop.
6. Keep humans in the loop at decision and permission boundaries.
7. Evaluate final outcomes, trajectories, handoff quality, permissions, and evidence.
8. Use trace artifacts to debug coordination failures backward from the observed problem.

## Module Structure

### 1. Multi-Agent as an Architectural Trade-Off

- Why single-agent systems hit limits
- When specialization, isolation, parallelism, or context pressure justify multiple agents
- Why “more agents” can increase cost, latency, and failure surface
- The “bag of agents” anti-pattern

### 2. Communication and Coordination Patterns

- Communication distance: close vs. distant agents
- Communication substrates:
  - direct calls
  - tool/function calls
  - shared artifact stores
  - workflow/graph state
  - message queues and mailboxes
  - HTTP/RPC boundaries
  - MCP-style agent-to-tool boundaries
  - A2A-style agent-to-agent boundaries
- Coordination patterns:
  - pipeline
  - fan-out/fan-in
  - supervisor/worker
  - peer-to-peer
  - agents-as-tools
  - human-orchestrated specialist workflows

### 3. Handoff Contracts and Shared Artifacts

Students will learn to pass structured artifacts instead of raw chat transcripts.

Required handoff concepts:

- **DiagnosisReport** — produced by Doctor
- **ContextBrief** — produced by Librarian
- **PatchSummary** or patch artifact — produced by Mechanic
- **VerificationReport** — produced by Doctor after Mechanic work

Good handoffs are typed or schema-constrained, source-grounded, explicit about uncertainty, and written for the receiving agent’s next task.

### 4. Human Checkpoints and Permission Boundaries

Module 9 treats human orchestration as a first-class production pattern.

The default workflow keeps humans involved at meaningful boundaries:

- approving or redirecting the repair boundary
- limiting allowed paths and tools
- deciding when a patch is acceptable
- interpreting residual risk after verification

Role boundaries:

- Doctor: read/check/report only
- Librarian: read/retrieve and memory writes only
- Mechanic: scoped code edits only
- Doctor verifies after Mechanic changes

### 5. Evaluation and Failure Forensics

The module introduces evals that inspect more than the final answer:

- **Outcome evals** — did the task succeed?
- **Trajectory evals** — did the specialists run in the right order?
- **Handoff evals** — did artifacts contain required fields and useful evidence?
- **Permission evals** — did agents stay within their boundaries?
- **Evidence evals** — were claims grounded in tests, files, docs, memory, or diffs?

Students will learn the trace-backward debugging move:

```text
bad final result
  ← bad verification?
  ← bad patch?
  ← bad context?
  ← bad diagnosis?
  ← bad request or routing?
```

## Hands-On Exercise: Codebase Team

The student exercise asks participants to build a small multi-agent workflow for `config-service`.

The scenario is intentionally concrete:

- a settings/environment test is failing
- Doctor diagnoses the failure
- Librarian retrieves relevant setup context from docs/memory/source
- a human approves the repair boundary
- Mechanic applies a focused fix through a coding-agent harness
- Doctor verifies the result
- Librarian may record the repair narrative

Students may use Pi, Claude Code, Codex, another coding-agent harness, or a human-assisted patch process for the Mechanic, as long as it fits the shared interface and handoff contract.

## Reference Implementation

Planned reference example:

```text
modules/09-MultiAgent/deliverables/examples/codebase-team/
```

Supporting local fixture:

```text
modules/09-MultiAgent/deliverables/examples/config-service/
```

The reference implementation should:

- copy and adapt the Doctor into the self-contained Module 9 example
- copy and adapt the Librarian into the self-contained Module 9 example
- use Pi coding agent as the Mechanic adapter
- keep Pi replaceable behind a common interface
- persist artifacts and run traces
- verify Mechanic changes with Doctor
- add deterministic evals after the first working flow exists

## Materials

- `slides/slides.md` — concept deck source
- `deliverables/slides.pdf` — generated student slide deck
- `deliverables/project/DESIGN.md` — exercise design document
- `deliverables/project/PLAN.md` — implementation planning scaffold
- `deliverables/project/STEPS.md` — step-by-step build guide
- `deliverables/project/EXERCISE.md` — student-facing exercise instructions
- `deliverables/examples/codebase-team/` — reference implementation
- `deliverables/examples/config-service/` — local target fixture

## Key Outcomes

By the end of Module 9, students should have:

- a working mental model for when multi-agent systems are worth the complexity
- a common interface for heterogeneous specialists
- structured handoff artifacts between agents
- a human-orchestrated Doctor → Librarian → Mechanic → Doctor loop
- explicit permission boundaries by role
- persisted traces and artifacts for debugging
- evals that inspect outcome, trajectory, handoff quality, permissions, and evidence
