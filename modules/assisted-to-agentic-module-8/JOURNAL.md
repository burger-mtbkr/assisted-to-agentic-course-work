# Module 8 Journal

## Entry 1: Build the Librarian, run it live, tune retrieval (in progress)

- **Prompt**: "do 7 - 9 ..." (same session as Module 7)
- **Tool**: Claude Code (VS Code extension)
- **Mode**: Direct execution; plan first (`librarian-agent/IMPLEMENTATION_PLAN.md`), then milestones 1-8
- **Context**: `modules/assisted-to-agentic-module-8/project/`, `agent-kit/`, `config-service/` and its Module 5 knowledge graph
- **Model**: Claude Opus 5.5 building; Gemini free tier inside (`gemini-3.5-flash`, `gemini-3.1-flash-lite`, `gemini-flash-lite-latest`, `gemma-4-26b-a4b-it`); `gemini-embedding-001` for vectors
- **Input**: Deep Agents on `agent-kit`. Durable Markdown notes, a SQLite index (chunks, vectors, entities, relationships), Git as episodic memory, a hybrid `retrieve_context` tool, three skills.
- **Output so far**:
  - `librarian-agent/`, 62 tests, ruff clean. Gemini index of `config-service`: 225 texts, embedded once and cached by content hash.
  - Embedding quota: the free tier counts each text in a batch as one request (100 a minute) and also caps tokens a minute. Batches are now paced and token-aware.
  - Retrieval quality, measured on real queries:
    - One document filled 8 of the top 12 hits (`ENV_SCRIPTS.md`); `openapi.json` filled 6 of 10. A cap of 2 hits per source fixes it.
    - A relative score floor tuned for one embedder starved the other. Gemini scores sit in 0.57-0.78; hashing scores spread over 0.1-0.5.
    - Summing chunk scores let `openapi.json` outrank the decision note that answers the question. A source now scores by its best evidence, and files reached through the graph inherit a discounted score.
    - Hashing scores "Why validate before saving?" at 0.000 against the stored decision; Gemini scores it 0.686 against a 0.567 distractor.
  - Live runs:
    - Source answers and Git history answers were cited correctly.
    - A weaker model saved an unverified user claim at confidence 1.0, with an invented date. Fixed in code: the store now dates user sources itself and caps user-only notes at 0.7.
    - A fresh session recalled the bad note, and it shaped the answer. A correction then superseded it, and a later answer used only the current note.
    - The model skipped retrieval and missed `appsettings.Development.json`.
- **Cost**: Free tier only. Two models' daily caps (20 requests) were reached.
- **Reflections**: (to write) memory amplifies whatever is stored, wrong or right; provenance rules belong in the write path.

### Open: reviewer findings to fix before this module is done

High:
1. Superseded notes come back into `recommended_context` through graph edges (`explains`, `supersedes`). Drop edges to superseded or archived notes unless history is asked for.
2. Note frontmatter round-trip: `split("---\n")` and the `## Rationale` partition can corrupt notes; one bad file can break `list()`. Anchor the parse, refuse newlines in fields, and make `list()` skip and report bad files.
3. Any non-refusal error ends the turn. A provider error mid-correction leaves the note files and the index inconsistent, and a retry writes a duplicate. Convert all errors to `ToolException`, sync statuses before embedding, refuse to supersede a non-current note, and `rev-parse --verify` commits.

Medium:
4. Git pathspec magic (`:(top)`, `:/`, `:!`) escapes the codebase scope: use `--literal-pathspecs`.
5. Note sources become unchecked `file:` nodes (`user, <date>`, `/codebase/...`). The cap can be dodged, and `UserGuide.md` is treated as a user source.
6. Index rebuild is neither atomic nor resumable: cache per batch, swap at the end.
7. No absolute relevance floor under Gemini, and no "weak evidence" gap.
8. False `tested_in` edges for `GlobalUsings.*.cs`.
9. `uncertain` and `archived` cannot be set from the agent.
10. `inspect`: traces, retrieval artifacts and index/note status drift; no tests for `inspection`, `cli`, `seeds` or `config`.
11. Knowledge-graph definitions and warnings are stored but never returned by `retrieve_context`.

Low: memory dir may sit inside the codebase; note-id regex accepts a trailing newline; traceback in chat without a key; `google-genai` not declared; README and plan drift (85% floor, three minutes, batch of 100).

Still to do: the live audit-logging supersede run (`gemma-4-26b-a4b-it`), the "main concepts" prompt, and the reflections file.
