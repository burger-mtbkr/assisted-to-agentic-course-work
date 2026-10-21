# librarian-agent

The Module 8 Librarian: a memory, knowledge and retrieval specialist for
`config-service`, built on Deep Agents and the shared `agent-kit`. It answers
questions with sources, remembers decisions and their rationale across
sessions, corrects them without losing their history, reads Git as episodic
memory, and prepares context for someone about to change the code. It never
edits the codebase.

Plan and decisions: `IMPLEMENTATION_PLAN.md`. Assignment:
`modules/assisted-to-agentic-module-8/project/`.

## Run it

From the repo root, with `librarian-agent/.env` holding `GEMINI_API_KEY` (copy
`.env.example`):

```bash
uv run --project librarian-agent librarian seed      # starter decision notes, from config-service's docs
uv run --project librarian-agent librarian index     # derived index: chunks, vectors, graph
uv run --project librarian-agent librarian           # converse (or: chat --ask "..." --ask "...")
uv run --project librarian-agent librarian retrieve "Why do duplicate names return 409?"
uv run --project librarian-agent librarian inspect   # notes, index, staleness, retrievals, sessions
uv run --project librarian-agent librarian inspect --note <id>
uv run --project librarian-agent librarian inspect --retrieval latest   # one retrieval, readable
```

Indexing with Gemini embeddings is paced to the free tier (100 embedded texts a
minute, plus a per-minute token budget), so a first build of `config-service`
takes about seven minutes.
Vectors are cached by content hash in `embeddings.db`, saved batch by batch,
so rebuilds re-embed only what changed (a rebuild with nothing new takes
seconds) and an interrupted build keeps what it paid for. A build goes into a
side file and replaces the index only when complete.
`LIBRARIAN_EMBEDDINGS=hashing` uses the deterministic offline embedder instead.

## Memory model

| Kind | Here | Where it lives |
|---|---|---|
| Working | the conversation and this turn's retrievals | in the session; logged under `conversations/`, `retrievals/` |
| Episodic | what happened | Git, through `git_log`, `git_show`, `file_history` (follows renames) |
| Semantic | facts about the code, docs, tests and decisions | the index: chunks + vectors, entities + relationships |
| Procedural | how to answer, remember, prepare change context | `skills/*/SKILL.md` |
| Durable | decisions and rationale the source does not state | `notes/*.md`, written only by `remember_decision` |

Source of truth is always the codebase and its Git history. Notes are durable
but can be wrong; the index is derived and rebuildable (`librarian index`).

## Tools

| Tool | What it does |
|---|---|
| `retrieve_context` | the one context call: semantic hits (chunks and notes, at most 2 per source, above both half the best score and the corpus mean plus one standard deviation), entity hits (knowledge-graph terms and aliases named in the question, files named as identifiers), one-hop graph expansion plus term -> file -> test, recommended context with reasons, and gaps. Superseded and archived notes are left out - of hits and of graph reach - and named in the gaps; a best hit under 3 standard deviations above the corpus is reported as weak evidence. Each call writes `retrievals/<time>-<query>.json`. |
| `remember_decision` | writes `notes/<date>-<title>.md` (statement, rationale, sources, confidence, entities) and indexes it at once; `supersedes` marks older current notes superseded. The store dates user sources itself and caps confidence at 0.7 unless a source is a file the index holds or a commit. Only indexed files and known knowledge-graph terms become graph links |
| `mark_memory_note` | marks a note uncertain, archived or current again, with the reason appended |
| `list_memory_notes`, `read_memory_note` | browse notes by status |
| `git_log`, `git_show`, `file_history` | read-only Git, scoped to the codebase with literal pathspecs; `git_show` accepts only hashes that are commits |
| `ls`, `read_file`, `glob`, `grep` | Deep Agents built-ins over `/codebase/` (git-visible files only, read-only) and `/skills/` |

The relationship graph starts from the Module 5 knowledge graph
(`config-service/knowledge/`: terms, aliases, warnings, `implemented_in`,
`documents`, term-to-term edges) and adds `tested_in` (C# `XTests.cs` ->
`X.cs`, TypeScript `x.test.ts` -> `x.ts`), `explains` (a note's sources and
terms) and `supersedes`.

## Boundaries

The Librarian has no filesystem write tool at all: `write_file`, `edit_file`,
`delete`, `execute`, `write_todos` and `task` are removed from what the model
is offered, every filesystem write is denied, and `/codebase/` is the
git-scoped read-only mount from `agent-kit` (no `.env`, no build output). All
writes go to `.librarian-memory/` (git-ignored): notes through
`remember_decision`, whose ids are slugs that cannot leave `notes/`; the
index; and the conversation, trace and retrieval logs.

## Settings

| Variable | Default |
|---|---|
| `GEMINI_API_KEY` | required for chat and Gemini embeddings; kept in `.env`, never in `os.environ` |
| `GEMINI_MODEL` | `gemini-flash-latest` (about 20 free requests a day per model; another free model can be named) |
| `LIBRARIAN_EMBEDDINGS` | `gemini`, or `hashing` |
| `LIBRARIAN_EMBEDDING_MODEL` | `gemini-embedding-001` (768 dimensions) |
| `LIBRARIAN_CODEBASE_PATH` | `../config-service` |
| `LIBRARIAN_KNOWLEDGE_DIR` | `<codebase>/knowledge` |
| `LIBRARIAN_MEMORY_DIR` | `.librarian-memory` |

## Tests

```bash
uv run --project librarian-agent pytest librarian-agent             # no provider calls
LIBRARIAN_LIVE=1 uv run --project librarian-agent pytest librarian-agent -m live   # real embeddings
uv run --project librarian-agent ruff check librarian-agent
```
