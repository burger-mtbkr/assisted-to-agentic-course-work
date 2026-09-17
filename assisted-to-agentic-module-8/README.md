# Module 8: Memory, Knowledge, and Retrieval

## The Librarian: Agentic Knowledge Management

Module 8 is the second specialist in the refreshed Phase 3 arc:

| Module | Specialist | Focus |
| --- | --- | --- |
| 7 | Doctor | Diagnose codebase health with scoped tools |
| 8 | Librarian | Remember, retrieve, and explain codebase knowledge |
| 9 | Mechanic | Make scoped changes with handoff and verification |

The central question for this module is:

> How does an agent remember what matters, retrieve the right knowledge, and preserve rationale over time?

The course scenario uses the `config-service` codebase, but the module is about agentic memory generally. The Librarian is not a coding agent. It answers questions, captures durable memory, connects sources, and prepares context for future work.

The larger takeaway is how to reason about memory and knowledge systems for agents: what should persist, what should be retrieved on demand, how to traverse different data structures, how to avoid stale clutter, and how to keep source artifacts authoritative.

## Learning objectives

By the end of the module, you can:

1. Distinguish ephemeral, episodic, semantic, and procedural memory.
2. Explain retrieval as context design, not just database plumbing.
3. Build a focused read-only Librarian with bounded memory-write tools.
4. Store durable notes with source, confidence, and rationale.
5. Use vector retrieval for semantic memory.
6. Use graph relationships for traceability and multi-hop questions.
7. Combine filesystem search, Git history, notes, vectors, and graph relationships into grounded answers.
8. State what the agent knows, where it learned it, and what remains uncertain.

## Memory model

- **Ephemeral / working memory:** current prompt, conversation state, scratch retrievals.
- **Episodic memory:** what happened before: Git history, implementation retrospectives, decision narratives.
- **Semantic memory:** durable facts about concepts, files, docs, tests, and architecture.
- **Procedural memory:** reusable workflows: skills, tool-use guidelines, retrieval procedures.

## Reference architecture

The reference implementation lives in:

```text
modules/08-Memory/deliverables/examples/librarian/
```

The reference implementation happens to use Python, a local CLI, provider-flexible model configuration, a read-only route to `config-service`, procedure files, and local memory artifacts under `.librarian-memory/`. Those choices are examples, not requirements. Students may use any language, agent framework, SDK, model provider, or embedding approach.

Required ideas include Git history, ADR-like durable Markdown notes, semantic recall, graph-style relationships, memory evolution, and retrieval/memory observability. The reference implementation demonstrates those ideas with a SQLite-backed memory graph and `sqlite-vec`; your exercise build can use a smaller local implementation if it preserves provenance, inspection, citations, and stale-memory handling. Source files remain the source of truth, while memory stores derived indexes and durable notes that are inspectable and rebuildable. The reference path stays local and bespoke while borrowing concepts from systems such as Supermemory, ArcadeDB, Graphify, Chroma, and Graphiti.

## Exercise path

You build the Librarian in milestones:

1. scoped identity and read-only codebase access
2. durable notes and episodic memory
3. curated indexing into local documents/chunks/entities
4. semantic recall with deterministic tests and optional real embedding checks
5. graph relationships and memory evolution/supersession
6. hybrid retrieval answers with citations, inspection artifacts, and gaps

The output should feel like a practical teammate: useful before design, debugging, or implementation work because it can retrieve prior rationale and source-grounded context without editing code.

The reference implementation is intentionally more complete than the minimum exercise build. You should come away able to reason about memory architecture and implement a clear vertical slice; the full SQLite memory graph is available as a concrete, inspectable example of the pattern.
