"""The Librarian on the team: the Module 8 Librarian's memory, turned into a ContextBrief.

It reads the diagnosis, retrieves over its index (docs, source, tests, notes, the
knowledge graph), adds Git history for the implicated files, and says what the Mechanic
may touch and what remains unknown. It writes only to its own memory: retrieval
artifacts, and - after a verified repair only - a repair note.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from librarian_agent.store import IndexUnavailable
from librarian_agent.tools import LibrarianTools

from codebase_team.artifacts import (
    AgentRequest,
    AgentResult,
    ContextBrief,
    DiagnosisReport,
    Evidence,
    PatchSummary,
    VerificationReport,
    read_artifact,
    write_artifact,
)


def words(identifier: str) -> str:
    """`ErrorMiddlewareTests.DuplicateApplicationNameException_MapsTo409` -> plain words."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", identifier.rsplit(".", 1)[-1])
    return re.sub(r"[_.]+", " ", re.sub(r"([A-Za-z])(\d)", r"\1 \2", spaced)).strip()


def is_test(path: str) -> bool:
    return ".UnitTests/" in path or ".test." in path


class LibrarianAdapter:
    name = "Librarian"

    def __init__(self, tools: LibrarianTools):
        self.tools = tools

    def handle(self, request: AgentRequest) -> AgentResult:
        artifacts = Path(request.inputs["artifacts"])
        try:
            if request.request_type == "retrieve_context":
                return self.retrieve(request.task_id, artifacts)
            if request.request_type == "remember_repair":
                return self.remember(request.task_id, artifacts, request.constraints.get("scenario"))
        except IndexUnavailable as exc:
            return AgentResult(self.name, "failed", f"The Librarian's memory is not ready: {exc}")
        return AgentResult(self.name, "failed", f"The Librarian does not handle {request.request_type!r}.")

    def _term_warnings(self, term_ids: set[str]) -> list[str]:
        facts = []
        for entity in self.tools.index.entities(["term"]):
            if entity["id"] in term_ids:
                for warning in entity["summary"].split("Warning: ")[1:]:
                    facts.append(f"{entity['name']} (knowledge graph): {warning.strip()}")
        return facts

    def retrieve(self, task_id: str, artifacts: Path) -> AgentResult:
        diagnosis = read_artifact(artifacts, DiagnosisReport)
        if diagnosis.status == "healthy":
            return AgentResult(self.name, "ok", "Nothing to brief: the diagnosis is healthy.")
        subjects = [words(t) for t in diagnosis.failing_tests] or [diagnosis.observed_error]
        code = [p for p in diagnosis.relevant_files if not is_test(p)]
        tests = [p for p in diagnosis.relevant_files if is_test(p)]
        queries = [f"{' '.join(subjects)} {diagnosis.suspected_cause}"]
        if code:
            queries.append(" ".join(Path(p).stem for p in code))
        results = [self.tools.retrieve_context(q) for q in queries]

        notes: dict[str, dict[str, Any]] = {}
        terms: set[str] = set()
        recommended: list[str] = []
        gaps: list[str] = []
        for result in results:
            notes |= {m["id"]: m for m in result["memories"] if m["status"] in ("current", "uncertain")}
            terms |= {h["id"] for h in result["entity_hits"] if h["id"].startswith("term:")}
            recommended += [
                c["source"] for c in result["recommended_context"] if not c["source"].startswith("note:")
            ]
            gaps += result["gaps"]
        for edge in self.tools.index.edges_touching([f"file:{p}" for p in code]):
            if edge.rel == "tested_in" and edge.src.removeprefix("file:") in code:
                tests.append(edge.dst.removeprefix("file:"))
        history = {p: self.tools.file_history(p)["commits"][:3] for p in code}

        facts = [f"note {n['id']} (confidence {n['confidence']}): {n['statement']}" for n in notes.values()]
        facts += self._term_warnings(terms)
        facts.append(
            f"The failing check is {', '.join(diagnosis.failing_tests) or diagnosis.failing_checks}."
        )
        docs = list(dict.fromkeys(p for p in recommended if p.endswith((".md", "openapi.json"))))
        evidence = [Evidence(f"note:{n['id']}", "memory", n["statement"]) for n in notes.values()]
        evidence += [Evidence(p, "doc", "recommended by hybrid retrieval") for p in docs[:4]]
        evidence += [Evidence(p, "source", "named by the diagnosis") for p in code]
        evidence += [Evidence(p, "test", "guards the implicated code") for p in dict.fromkeys(tests)]
        evidence += [
            Evidence(f"git {c['commit']}", "git", f"{c['date']} {c['subject']} ({path})")
            for path, commits in history.items()
            for c in commits
        ]
        constraints = []
        if code:
            constraints.append(f"Edit only {', '.join(code)}: the diagnosis names it as the code under test.")
        if tests:
            constraints.append(
                f"Do not edit {', '.join(dict.fromkeys(tests))}: tests encode the contract; a repair that "
                "changes the test to match the code hides the regression."
            )
        if notes or terms:
            constraints.append("Keep the behaviour the remembered decisions and the API contract describe.")
        gaps = list(dict.fromkeys(gaps)) + [
            "Notes are durable memory, not source of truth: the tests and openapi.json are what the "
            "patch must satisfy."
        ]
        brief = ContextBrief(
            task_id=task_id,
            relevant_docs=docs,
            relevant_memory_notes=list(notes),
            relevant_source_files=code,
            relevant_tests=list(dict.fromkeys(tests)),
            git_evidence=[
                f"{c['commit']} {c['date']} {c['subject']}" for commits in history.values() for c in commits
            ],
            facts=facts,
            suggested_constraints=constraints,
            gaps=gaps,
            evidence=evidence,
            confidence=0.85 if notes else 0.6,
        )
        path = write_artifact(artifacts, brief)
        return AgentResult(
            self.name,
            "ok",
            f"{len(facts)} facts, {len(notes)} memory notes, edit boundary: {', '.join(code) or 'unclear'}",
            artifacts=[str(path), *(r["artifact"] for r in results)],
            evidence=evidence[:3],
            confidence=brief.confidence,
            next_actions=["Human: approve or narrow the edit boundary."],
        )

    def remember(self, task_id: str, artifacts: Path, scenario: str | None) -> AgentResult:
        verification = read_artifact(artifacts, VerificationReport)
        if verification.status != "verified":
            return AgentResult(
                self.name, "blocked", f"Not remembered: verification is {verification.status}, not verified."
            )
        diagnosis = read_artifact(artifacts, DiagnosisReport)
        brief = read_artifact(artifacts, ContextBrief)
        patch = read_artifact(artifacts, PatchSummary)
        drill = f" (repair drill: seeded scenario {scenario!r})" if scenario else ""
        failing = ", ".join(t.rsplit(".", 1)[-1] for t in diagnosis.failing_tests) or diagnosis.observed_error
        artifact_paths = [str(artifacts / a.FILENAME) for a in (DiagnosisReport, ContextBrief, PatchSummary)]
        saved = self.tools.remember_decision(
            title=f"Repair {task_id}: {failing}"[:80],
            statement=(
                f"When {failing} fails{drill}, the verified repair was: {patch.intent} "
                f"Changed: {', '.join(patch.files_changed)}. Tests left as the contract."
            ),
            rationale=(
                f"Diagnosis: {diagnosis.suspected_cause}. Context: {'; '.join(brief.facts[:2])}. "
                f"Verification: {verification.recommendation}"
            ),
            sources=[
                *patch.files_changed,
                *brief.relevant_tests,
                *artifact_paths,
                str(artifacts / "verification.json"),
            ],
            confidence=0.9,
            entities=[],
        )
        return AgentResult(self.name, "ok", f"Remembered as note {saved['remembered']}", [saved["file"]])
