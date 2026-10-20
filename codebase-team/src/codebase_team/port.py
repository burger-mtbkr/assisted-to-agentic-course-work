"""The one boundary every specialist sits behind. The orchestrator knows nothing else about them."""

from __future__ import annotations

from typing import Protocol

from codebase_team.artifacts import AgentRequest, AgentResult


class AgentPort(Protocol):
    name: str

    def handle(self, request: AgentRequest) -> AgentResult: ...
