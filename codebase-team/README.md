# codebase-team

The Module 9 Codebase Team: the Doctor (Module 7), the Librarian (Module 8) and a
new Mechanic, coordinated as a deterministic pipeline with a human approval gate.
Agents do not chat with each other; they hand each other typed artifacts, and a
trajectory log records every step.

```text
Doctor.diagnose -> Librarian.retrieve_context -> approval proposed
   (stop: a human approves or narrows the boundary)
-> Mechanic.patch (only if approved) -> Doctor.verify -> Librarian.remember_repair (optional)
```

Plan and decisions: `IMPLEMENTATION_PLAN.md`. Assignment:
`modules/assisted-to-agentic-module-9/project/`.

## Run it

From `codebase-team/` (needs `.env` with the free-tier `GEMINI_API_KEY`, and the
Librarian's index built: `uv run --project ../librarian-agent librarian index`):

```bash
uv run codebase-team run --scenario duplicate-name-status   # diagnose + brief, stop at the gate
uv run codebase-team continue <task>                        # refused: nothing approved yet
uv run codebase-team approve <task> --path src/ConfigApi.Service/Middleware/ErrorMiddleware.cs \
    --rationale "409 is the contract; the middleware is wrong, not the test"
uv run codebase-team continue <task> --remember             # patch, verify, remember
uv run codebase-team evals <task>                           # coordination evals (23 on a full run)
uv run codebase-team inspect <task>                         # the run, rebuilt from its artifacts
```

`run ... --approve PATH --rationale R` does the whole approved path in one
command; `--mechanic human` swaps the live agent for a person editing the
workspace by hand. The Mechanic may run the service tests only with
`--allow-tests`: running them runs the code it just wrote (in the run's copy,
with a minimal environment that carries no credentials), so a human opts in.

`config-service` itself is green, so `--scenario duplicate-name-status` seeds a
regression into the run's copy (never the original): `ErrorMiddleware` returns
400 instead of 409 for a duplicate application name. The fix is ambiguous from
the failing test alone - change the code, or the test? - and the Librarian's
memory (the 409 decision note, the knowledge-graph warning, `openapi.json`) is
what settles it.

## The specialists

| Specialist | Implementation | Boundary |
|---|---|---|
| Doctor | adapter over `doctor_agent.tools.run_check` in the run workspace; parses the .NET test output, reads only the failing test at its line and the code it is named after | read-only |
| Librarian | adapter over `librarian_agent.tools.LibrarianTools` and its Module 8 memory: hybrid retrieval, notes, knowledge-graph warnings, `file_history` | writes only its own memory (retrieval artifacts; a repair note only after verification) |
| Mechanic | Deep Agents + Gemini (`agent-kit`), the workspace mounted with `GrantedWriteBackend` writing only the approved paths, the `repair-issue` skill, `run_tests` if the approval allows; or a human behind the same port | edits only approved paths, in the run's copy |

All three sit behind one `AgentPort` (`handle(AgentRequest) -> AgentResult`).

## Artifacts

`.codebase-team-runs/<task>/` (git-ignored):

| Path | What |
|---|---|
| `run.json` | source path, its HEAD and fingerprint, the scenario |
| `workspace/` | the copy: git-visible files only (no `.env`, no `node_modules`), committed as a baseline |
| `artifacts/diagnosis.json` | `DiagnosisReport`: failing checks and tests, observed error, relevant files, suspected cause, evidence, uncertainty |
| `artifacts/context_brief.json` | `ContextBrief`: docs, notes, source, tests, Git evidence, facts, suggested constraints, gaps |
| `artifacts/approval.json` | `ApprovalRecord`: proposed as not approved; the human's decision replaces it |
| `artifacts/patch_summary.json` | `PatchSummary`: files changed, diff summary, rationale, risks, verification request, the diff as evidence |
| `artifacts/verification.json` | `VerificationReport`: checks, pass/fail, remaining failures, recommendation |
| `trajectory.jsonl` | every request, result (with whether the workspace changed), artifact, approval, block and outcome |
| `mechanic/` | the Mechanic's own conversation and trace |

Every artifact validates itself on write and on read; an incomplete handoff is
an error by name, not a silent pass.

## Guarantees and where they live

| Guarantee | Where |
|---|---|
| no patch without a granted approval | `mechanic.approval_gate` fails closed on a missing, malformed or refused approval |
| edits only inside the approval | `GrantedWriteBackend` refuses other writes; `finish_patch` reverts anything else found in the diff and records it |
| the original is untouched | the run works on a copy; its fingerprint is checked by the evals |
| Doctor and Librarian change nothing | the workspace is fingerprinted around every step |
| success only when verified | the claim comes from `VerificationReport.status`; an eval checks it |

## Tests

```bash
uv run pytest      # 23 tests, no model calls
uv run ruff check .
```

The tests run the whole team on a miniature `config-service` whose `check.py`
prints .NET-shaped output: the approved path end to end (with the real Deep
Agents Mechanic driven by a scripted model), the refusal without approval, a
refused approval, an out-of-bounds edit refused by the mount, a human's
out-of-bounds edit reverted and flagged, a corrupted handoff and a patch before
approval caught by the evals, and a healthy codebase stopping after diagnosis.
