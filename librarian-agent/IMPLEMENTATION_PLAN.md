# Librarian Agent - Implementation Plan

Parts 0-2 of `modules/assisted-to-agentic-module-8/project/STEPS.md`: the
exercise translated into this repo's workflow, the memory problem framed, and
`PLAN.md`'s milestones filled in before any code.

## Part 0 - how this maps onto the workflow already in use

| This repo's habit | Applied here |
|---|---|
| Plan before act, in a file next to the code | this file |
| Carry earlier modules forward instead of rebuilding | `agent-kit` (Module 7's mount, Gemini wiring, turn recording); the Module 5 knowledge graph YAML becomes the Librarian's starting relationship graph |
| Real checks, not mocked confidence | deterministic tests for every store and the retrieval path, then the EXERCISE.md prompts run against Gemini, then a `reviewer` pass |
| Journal + reflections per module | `modules/assisted-to-agentic-module-8/JOURNAL.md`, `INTEGRATE-REFLECTIONS.md` (answering EXERCISE.md's debrief questions) |

Gap the course's process adds that this repo's did not have: an explicit
"retrieval-quality issue recorded and tuned" step (Milestone 4). It goes in
the journal with before/after numbers.

## Part 1 - the memory problem, for `config-service`

1. **Source of truth**: the code, tests, `context/*.md`, `openapi.json`,
   `knowledge/*.yaml`, and git history. The Librarian reads them; it never
   edits them.
2. **Worth durable memory**: decisions and their rationale that the code does
   not state - "why scan-and-cache instead of a GSI", "why errors map to 409",
   a correction someone made in conversation. Not facts the code already
   states plainly.
3. **Semantic recall answers**: questions worded differently from the source -
   "why validate before saving?" finding "validated at write time".
4. **Relationships worth traversing**: term -> implemented_in -> file ->
   tested_in -> test; doc -> documents -> term; note -> explains -> file or
   term; note -> supersedes -> note; the knowledge graph's own term-to-term edges.
5. **Inspectable after each run**: notes (Markdown), the SQLite index, one
   JSON artifact per retrieval, conversation and trace JSONL.
6. **Minimal vertical slice**: one hybrid `retrieve_context` tool over all of
   the above, plus note write/list/read, plus three git tools.

## Decisions

| Question | Answer |
|---|---|
| Language / framework | Python 3.13, Deep Agents, on `agent-kit` (same as the Doctor) |
| Model | Gemini free tier (`GEMINI_MODEL`, default `gemini-flash-latest`) |
| Embeddings | `gemini-embedding-001` at 768 dimensions (documents and queries embedded with their own task types), in batches of at most 90 texts and about 15k tokens, one batch a minute (the free tier counts every text as a request and caps tokens a minute), cached by content hash in `embeddings.db`. `LIBRARIAN_EMBEDDINGS=hashing` swaps in a deterministic feature-hashing embedder: what every test uses, and an offline fallback. The index records which embedder built it and refuses to mix. |
| Codebase | `../config-service`, mounted read-only at `/codebase/` through `agent-kit`'s git-scoped mount |
| Memory directory | `.librarian-memory/` (git-ignored): `notes/*.md`, `librarian.db`, `retrievals/`, `conversations/`, `traces/`. The only place the Librarian writes. |
| Write restriction | No filesystem write tools at all (harness profile + deny-all write permission + read-only mount). Notes are written only by `remember_decision`, whose ids are slugs, so a note path cannot leave `notes/`. |
| Notes format | Markdown with YAML frontmatter holding every field: `id, title, statement, rationale, status (current / uncertain / superseded / archived), confidence, sources, entities, supersedes, superseded_by, created`. The body below it is a rendering for people; keeping the note in YAML means no content can be mistaken for structure. |
| Index | SQLite: `documents` (path, sha1, kind), `chunks` (text, lines, vector), `entities`, `relationships` (with evidence and confidence), `meta`. Derived and rebuildable (`librarian index`, built into a side file and swapped in when complete); notes are the durable part. |
| Graph | Imported from `config-service/knowledge/` (Module 5) plus derived edges: C# `XTests.cs` -> `X.cs` and TS `x.test.ts` -> `x.ts` (`tested_in`), note sources (`explains`), corrections (`supersedes`). |
| Git (episodic) | `git_log`, `git_show`, `file_history` - read-only, scoped to the codebase directory; `file_history` follows renames, which matters because `config-service` moved at the repo reorg. |
| Inspect | `librarian inspect` (notes, index stats, staleness, recent retrievals, sessions) and `librarian retrieve "<query>"` (runs hybrid retrieval with no chat model). |

## Milestones (PLAN.md 1-8)

1. **Boundary and source access** - config, prompt, agent, CLI; mount + write denial. Check: "What is this service? Cite files you read."; a write attempt fails.
2. **Durable notes** - `notes.py`, `remember_decision` / `list_memory_notes` / `read_memory_note`. Check: remember, restart, recall; open the `.md`.
3. **Episodic memory** - `history.py`. Check: "What changed recently in this service? Cite Git evidence."
4. **Semantic recall** - `embeddings.py`, `store.py`, `indexer.py`. Check: store the write-time-validation decision, ask "Why validate before saving?". Record a quality issue and tune.
5. **Relationship graph** - knowledge-graph import + derived edges. Check: a term expands to its files and their tests.
6. **Hybrid retrieval** - `retrieval.py`: `semantic_hits, entity_hits, graph_expansion, recommended_context, gaps`, each item with provenance; superseded notes filtered; one JSON artifact per call. Check: the three EXERCISE.md retrieval prompts.
7. **Memory evolution** - `supersedes` in `remember_decision`. Check: remember the audit-log fact, correct it, ask again; only the current fact is used, history still explainable.
8. **Final verification** - tests, ruff, every EXERCISE.md prompt against Gemini, `librarian inspect`.

## Scope reductions

- `config-service` is a C# service, not the curriculum's Python one, so the
  EXERCISE prompts that assume Python facts ("config sets validated at write
  time", "environment-specific overrides", "audit logging") are asked as
  written: where this codebase has no such thing, the right answer is a gap,
  and that is part of what is being tested.
- Pure-Python cosine search, no `sqlite-vec`: a few hundred chunks do not
  need an extension, and Windows wheels are one less thing to break.
