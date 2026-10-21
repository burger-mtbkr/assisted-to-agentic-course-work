# Module 8 - Integrate & Reflect

Module 8 ships no `project/INTEGRATE.md`. Its `EXERCISE.md` ends with five debrief
questions, answered below from what building and running the Librarian showed.

## Summary

**What I did:** Built the Librarian (`librarian-agent/`) on Deep Agents and the
shared `agent-kit`, as a read-only memory specialist for `config-service`. It has:

- durable Markdown decision notes, with sources, confidence and status
- a rebuildable SQLite index: chunks with Gemini vectors, plus a relationship
  graph started from the Module 5 knowledge graph
- Git as episodic memory
- one hybrid `retrieve_context` call that returns hits, graph links,
  recommended reading and gaps, and leaves a JSON artifact per call
- an `inspect` view of the whole memory state

I verified it live against Gemini: cited answers, cross-session recall,
correcting a wrong memory, and the audit-logging supersession scenario. A
reviewer pass found three high-severity problems and I fixed all of them.

**How it went:** The retrieval mechanics were quick. What took the time was
tuning on real scores, and finding all the ways a wrong or stale memory could
still reach an answer.

**What I learned:** Memory design is mostly about what not to return:
superseded notes, unverified claims at full confidence, a long document
crowding out the one note that answers. And every rule that protects memory has
to live in the store, because the model will skip the skill that describes it.

---

## 1. What did the agent remember that would otherwise be rediscovered?

Decisions the code does not state:

- **Why reads scan and cache** instead of querying an index, and when to
  revisit that.
- **Why duplicates are 409, not 400.** The Module 9 team used exactly this
  note to decide which side of a failing test was wrong.
- **Why secrets live in `.env` but settings in `appsettings.json`.**
- **That unit tests do not prove the DynamoDB layer.** A Module 1 outage taught
  this, and nothing in the code says it.
- **A user's corrections:** audit logs store hashes, not raw values, with the
  superseded "raw values" note kept as history.
- **A verified repair narrative**, written by the Module 9 team after its drill.

Without notes, each of these is rediscovered by reading
`context/ARCHITECTURE.md` end to end, or by asking someone. With them, one
retrieval returns the decision, its rationale and its sources.

## 2. Which retrieved items came from source files, Git, notes, vector recall, or graph expansion?

Every retrieval artifact says so per item. Two examples:

| Question | Notes | Vector recall | Graph | Git |
|---|---|---|---|---|
| "Why do duplicate application names return 409?" | the 409 decision note, ranked first (0.78) | `openapi.json` 409 responses, `DuplicateApplicationNameException.cs`, `ARCHITECTURE.md` | the note's `explains` links to `ErrorMiddleware.cs` and `ErrorMiddlewareTests.cs`; `term:application` to its four implementation files | not used, so a gap says to ask `file_history` |
| "What changed recently?" | - | - | - | `git_log` then `git_show` on three commits, each cited by hash and date |

The graph mattered most where words did not reach. `ErrorMiddleware.cs` never
appeared in the vector hits for the 409 question; only the note's curated link
brought it in.

## 3. Which memories should be current, uncertain, archived, or superseded?

- **Current:** the four seeded decisions taken from `config-service`'s docs
  (confidence 0.9-0.95, sources in the codebase); the corrected key-validation
  note; the "hashes" audit decision; the repair narrative.
- **Superseded:** "config sets are validated at write time for fast reads".
  This was a user claim that the source contradicts: only key format is
  validated, and there are no "config sets". It was superseded by a note that
  says what the code actually does. Likewise "audit logs store raw values".
- **Uncertain:** a user-only claim no source backs, like the audit-hashes
  decision (capped at 0.7). Marking it uncertain until audit logging exists
  would be honest. `mark_memory_note` exists for exactly that.
- **Archived:** anything about a part of the system that is removed. Nothing
  qualifies yet.

The store now enforces the transitions:

- only a current or uncertain note can be superseded
- superseded and archived notes are hidden from current answers, including
  through graph links
- history stays reachable with `include_superseded`

## 4. Where did retrieval help, and where did the agent still need to verify against source?

**It helped:**

- the 409 decision ranked first
- the audit-logging history answered in one call
- a broad "main concepts" question was answered from `ABOUT.md`,
  `ARCHITECTURE.md` and the knowledge graph in five rounds, with sources

**Verification was still needed:**

- **A bad memory looked authoritative.** The stored "fast reads" claim made a
  fresh session repeat it as fact, even while the source it read showed only
  key-format validation. The skill says the source wins; the answer did not
  apply that until the note was corrected.
- **Literal search missed a file.** The agent skipped retrieval for a literal
  grep on "environment"/"override" and missed `appsettings.Development.json`.
  Semantic recall did not surface that small JSON file either. Small
  config files are a blind spot in a chunk-similarity index.
- **Weak matches were still returned.** An off-topic question still got 8
  confident-looking hits. Only the "weak evidence" gap, calibrated on measured
  scores, says the index does not cover it.

## 5. How would this design change for a non-code domain (sales, support, research, operations)?

- **Source of truth changes shape.** CRM records, tickets, papers and runbooks
  have no `git ls-files`. Visibility rules ("what may the agent see?") become
  permissions per record and per customer, not a `.gitignore`.
- **Episodic memory is the system's own history:** ticket timelines, deal
  stages, experiment logs. A `file_history` becomes "how did this account or
  incident evolve".
- **The graph carries the domain's relationships:** customer -> contract ->
  product -> incident, or paper -> method -> dataset. Not
  `implemented_in` / `tested_in`.
- **Supersession gets stricter.** Prices, policies and on-call rotations go
  stale on a date. Notes would need validity windows (`valid_until`), not just
  "superseded by".
- **Provenance and confidence matter more.** A support agent quoting a
  superseded refund policy causes real harm. The same rules apply - dated
  sources, capped confidence for hearsay, stale memory hidden from current
  answers - with an audit trail of who changed what.
- **Embeddings and evaluation would be domain-tuned.** The measured
  "weak evidence" threshold would need recalibrating per corpus. It is a
  property of the data, not a constant.

## What I'd carry into Module 9

- The Librarian's value to a team is the brief: facts with sources, the edit
  boundary, the gaps. It has to be compact enough to hand to a Mechanic.
- Notes beat chunks for decisions. Index source for "where", keep decisions as
  notes for "why".
- Every agent needs a per-turn budget. It is a property of the harness, not of
  any one prompt.
