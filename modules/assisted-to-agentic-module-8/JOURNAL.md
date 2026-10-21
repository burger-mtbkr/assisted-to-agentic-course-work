# Module 8 Journal

## Entry 1: Build the Librarian, run it live, tune retrieval

- **Prompt**: "do 7 - 9. I need a summary of what we did for 7 - 9 in a readme
  file with notes ... i need to speak to it in a playback" (same session as
  Module 7)
- **Tool**: Claude Code (VS Code extension)
- **Mode**: Direct execution. Plan first
  (`librarian-agent/IMPLEMENTATION_PLAN.md`, which maps the exercise onto this
  repo's workflow), then milestones 1-8.
- **Context**: `modules/assisted-to-agentic-module-8/project/`, `agent-kit/`,
  `config-service/` and its Module 5 knowledge graph
- **Model**: Claude Opus 5.5 building. Gemini free tier inside
  (`gemini-3.5-flash`, `gemini-3.1-flash-lite`, `gemini-flash-lite-latest`,
  `gemma-4-26b-a4b-it`); `gemini-embedding-001` for vectors.
- **Input**: Deep Agents on `agent-kit`; durable Markdown notes; a SQLite index
  (chunks, vectors, entities, relationships); Git as episodic memory; one hybrid
  `retrieve_context` tool; three skills.
- **Output**:
  - `librarian-agent/`; a Gemini index of `config-service` (225 texts, cached by
    content hash).
  - **Embedding quota:** the free tier counts each text in a batch as one
    request (100 a minute) and also caps tokens a minute, so batches are paced
    and token-aware.
  - **Retrieval quality, measured on real queries (the Milestone 4 "record a
    quality problem and tune it"):**
    - *Over-retrieval from one source:* `ENV_SCRIPTS.md` took 8 of the top 12
      hits for "environment-specific overrides", `openapi.json` 6 of 10 for the
      409 question. Fix: at most 2 hits per source.
    - *A floor tuned for one embedder starved the other:* Gemini scores sit in
      0.57-0.78, hashing scores spread over 0.1-0.5. Fix: "half the best score"
      combined with "above the corpus mean plus one standard deviation" (Entry 2).
    - *Summing chunk scores:* `openapi.json`'s two chunks (1.44) outranked the
      note that answers the question (0.78). Fix: a source scores by its best
      evidence, and a file reached through the graph inherits 90% of its seed's
      score, so the note's links to `ErrorMiddleware.cs` and its tests surface.
    - *Meaning vs words:* "Why validate before saving?" scores 0.000 under
      hashing against the stored decision, while Gemini scores it 0.686 against
      a 0.567 distractor. This is why the course wants a real-embedding path
      next to the deterministic one.
  - **Live runs:**
    - Source and Git questions came back cited (files with lines, commit hashes).
    - A weaker model saved an unverified user claim at confidence 1.0 with an
      invented date. Fixed in the store: user sources are dated by the store,
      and user-only notes are capped at 0.7.
    - A fresh session recalled that bad note, and it shaped the answer. A
      correction superseded it, and later answers used only the current note.
    - Audit logging on Gemma: the agent gave change context for a future
      Mechanic, remembered "raw values", superseded it with "hashes", then
      answered "what did we decide before?" with both, correctly labelled. The
      model asked for confidence 1.0 twice; the store saved 0.7.
    - The model once skipped retrieval for a literal grep and missed
      `appsettings.Development.json`.
- **Cost**: Free tier only. Two models' daily caps (20 requests each) were
  reached.
- **Reflections**: memory amplifies whatever is stored, wrong or right. The
  provenance rule only held once it moved from the skill's wording into the
  write path. Weaker models skip procedures; stores do not.

## Entry 2: Reviewer findings fixed, a budget per turn, final live checks

- **Prompt**: "continue" (next day)
- **Tool**: Claude Code; findings from a `reviewer` subagent pass on the
  previous day's code
- **Mode**: Fix every finding, test each fix, re-verify live
- **Context**: the reviewer's report (3 high, 8 medium, 6 low), the live
  memory, `agent-kit/`
- **Model**: Claude Opus 5.5; Gemini `gemini-flash-latest`,
  `gemini-flash-lite-latest`, `gemini-3.1-flash-lite` for the live checks
- **Input / Output** (finding: fix):
  - **Superseded notes leaked back through graph edges:** edges to stale notes
    are dropped. Only the successor's `supersedes` edge is kept, as history,
    and it is never walked; a gap points to `include_superseded`.
  - **Note corruption:** the whole note now lives in anchored YAML frontmatter,
    so no title or statement can be mistaken for structure. Newlines are
    refused in titles, sources and entities. An unreadable file is reported,
    not fatal. The 8 existing notes were migrated once.
  - **Half-applied corrections:** every tool failure becomes a tool error. A
    correction syncs index statuses before embedding, so an embedding failure
    only means "saved, not yet searchable". Only a current note can be
    superseded, and `git_show` checks the hash is a commit.
  - **Pathspec magic** (`:(top)`, `:/`, `:!`): `--literal-pathspecs`, and `:`
    paths are refused. Log records are NUL-separated.
  - **Unchecked note links:** a note links only to files the index holds and to
    known terms. The confidence cap lifts only for a source the index can
    check (an indexed file or a real commit). `UserGuide.md` is no longer
    mistaken for a user statement.
  - **Index rebuilds:** cached batch by batch in a separate `embeddings.db`,
    built into a side file and swapped in only when complete. Test: a
    failure mid-build leaves the old index usable and keeps the paid-for batch.
  - **Relevance and weak evidence:** the corpus-relative floor above, plus a
    "weak evidence" gap. The threshold came from measurement: answerable
    questions stood 3.5-7.4 standard deviations above the corpus, and "how do
    I bake sourdough bread?" stood at 2.8, so the gap fires below 3.0.
  - **Bogus `tested_in` edges** for `GlobalUsings.*.cs`: gone (19 edges -> 14).
  - **`uncertain` and `archived`:** a new `mark_memory_note` tool.
  - **`inspect`:** shows drift (notes not indexed, statuses that disagree,
    files added since indexing, unreadable notes), the latest trace and
    questions, and `--retrieval latest`.
  - **Knowledge-graph data:** term hits now carry their definition and warnings.
  - **Low findings:** a memory dir inside the codebase is refused; note ids
    are fullmatched; chat without a key gives a clear refusal; `google-genai`
    is declared; doc drift fixed.
  - **Tests:** 62 -> 91, adding config, CLI, seeds, inspect and tools.
  - **Round budget:** the "main concepts" prompt read file after file for 20
    rounds and spent `gemini-flash-latest`'s whole day without answering.
    Module 6's hand-rolled loop had a round limit; the framework loop did not.
    `agent-kit` now has `RoundBudget` (12 model calls a turn, the last one told
    to answer). Probing showed Gemini ignores `tool_choice="none"`, and still
    calls a tool with no tools declared when the history holds tool calls, so
    the budget also drops tool calls from the final reply. Verified live:
    capped at 3, a "list every class" question ended in exactly 3 calls with
    an answer.
  - **Final live run:** "main concepts" on `gemini-flash-lite-latest` answered
    in 5 rounds. Application, ConfigurationItem and FeatureFlag, each with
    model / controller / service / repository / table and cited sources, and
    the UI noted as not traversed.
- **Cost**: Free tier only.
- **Reflections**: the reviewer's top finding was the module's own point.
  Supersession has to be enforced everywhere memory can be reached, and the
  graph was a second door. Most fixes moved a rule from "the model should"
  to "the store will": dates, caps, statuses, links. And "a framework does
  the loop" does not include "the loop stops": a budget is a design decision
  the course's Module 6 made explicit and Module 8 nearly lost.
