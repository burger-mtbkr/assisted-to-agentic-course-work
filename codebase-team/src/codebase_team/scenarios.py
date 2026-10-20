"""Seeded regressions for repair drills.

`config-service` is green, so a team run needs a failure to repair. A scenario edits the
run's workspace copy - never the original - before its baseline commit, so the defect is
simply "how the code is" to every specialist. It is the counterpart of the curriculum
fixture's planted settings failure.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class ScenarioError(ValueError):
    """An unknown scenario, or one whose target no longer looks as expected."""


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    path: str
    find: str
    replace: str


SCENARIOS = {
    s.name: s
    for s in [
        Scenario(
            name="duplicate-name-status",
            description=(
                "ErrorMiddleware maps DuplicateApplicationNameException to 400 Bad Request instead of "
                "409 Conflict. ErrorMiddlewareTests.DuplicateApplicationNameException_MapsTo409 fails."
            ),
            path="src/ConfigApi.Service/Middleware/ErrorMiddleware.cs",
            find=(
                "catch (DuplicateApplicationNameException ex)\n        {\n"
                "            await WriteResponseAsync(context, StatusCodes.Status409Conflict, "
                '"Conflict", ex.Message, ex);'
            ),
            replace=(
                "catch (DuplicateApplicationNameException ex)\n        {\n"
                "            await WriteResponseAsync(context, StatusCodes.Status400BadRequest, "
                '"Bad Request", ex.Message, ex);'
            ),
        ),
    ]
}


def apply(workspace: Path, name: str) -> Scenario:
    scenario = SCENARIOS.get(name)
    if scenario is None:
        raise ScenarioError(f"Unknown scenario {name!r}; known: {', '.join(SCENARIOS)}")
    target = workspace / scenario.path
    with target.open(encoding="utf-8", newline="") as handle:
        text = handle.read()
    newline = "\r\n" if "\r\n" in text else "\n"
    find, replace = (part.replace("\n", newline) for part in (scenario.find, scenario.replace))
    if text.count(find) != 1:
        raise ScenarioError(f"{scenario.path} no longer contains the code {name!r} changes")
    with target.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text.replace(find, replace))
    return scenario
