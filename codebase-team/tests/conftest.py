"""A miniature config-service the whole team can run against with no model provider.

`check.py` stands in for `dotnet test`: it fails with .NET-shaped output while
ErrorMiddleware maps duplicate names to 400, and passes once they map to 409 again.
"""

import subprocess
import sys
from pathlib import Path

import pytest
from agent_kit.testing import ScriptedModel, call, calls
from langchain_core.messages import AIMessage
from librarian_agent.embeddings import HashingEmbedder
from librarian_agent.indexer import build_index
from librarian_agent.notes import NoteStore
from librarian_agent.store import EmbeddingCache, MemoryIndex
from librarian_agent.tools import LibrarianTools

from codebase_team.doctor import DoctorAdapter
from codebase_team.librarian import LibrarianAdapter
from codebase_team.mechanic import AgentMechanic, HumanMechanic
from codebase_team.orchestrator import Team, TeamConfig

MIDDLEWARE = "src/ConfigApi.Service/Middleware/ErrorMiddleware.cs"
MIDDLEWARE_TESTS = "src/ConfigApi.Service.UnitTests/Middleware/ErrorMiddlewareTests.cs"
TEST_NAME = (
    "ConfigApi.Service.UnitTests.Middleware.ErrorMiddlewareTests.DuplicateApplicationNameException_MapsTo409"
)

CHECK = f'''
import pathlib, sys
here = pathlib.Path.cwd()
code = (here / "{MIDDLEWARE}").read_text()
block = code.split("catch (DuplicateApplicationNameException ex)")[1].split("}}")[0]
if "Status409Conflict" in block:
    print("Passed!  - Failed:     0, Passed:     3, Skipped:     0, Total:     3, Duration: 5 ms")
    sys.exit(0)
print("  Failed {TEST_NAME} [1 ms]")
print("  Error Message:")
print("   Assert.Equal() Failure: Values differ")
print("Expected: 409")
print("Actual:   400")
print("  Stack Trace:")
print("     at {TEST_NAME}() in " + str(here / "{MIDDLEWARE_TESTS}") + ":line 4")
print("Failed!  - Failed:     1, Passed:     2, Skipped:     0, Total:     3, Duration: 5 ms")
sys.exit(1)
'''

FILES = {
    MIDDLEWARE: (
        "public class ErrorMiddleware\n{\n    public async Task InvokeAsync(HttpContext context)\n    {\n"
        "        try { await _next(context); }\n"
        "        catch (DuplicateApplicationNameException ex)\n        {\n"
        "            await WriteResponseAsync(context, StatusCodes.Status409Conflict, "
        '"Conflict", ex.Message, ex);\n'
        "        }\n    }\n}\n"
    ),
    MIDDLEWARE_TESTS: (
        "public class ErrorMiddlewareTests\n{\n"
        "    public async Task DuplicateApplicationNameException_MapsTo409()\n"
        "    {\n        Assert.Equal(StatusCodes.Status409Conflict, statusCode);\n    }\n}\n"
    ),
    "context/ARCHITECTURE.md": (
        "# Architecture\n\n## Error handling\n\nErrorMiddleware maps duplicate application names to "
        "409 Conflict and validation failures to 400.\n"
    ),
    "knowledge/nodes/terms.yaml": (
        "nodes:\n  - id: error_response\n    type: domain_term\n    area: api\n    name: ErrorResponse\n"
        "    definition: The JSON error body.\n    aliases: [ErrorMiddleware]\n"
        "    warnings: [A duplicate application name returns 409 Conflict.]\n"
        f"    source_files: [{MIDDLEWARE}]\n    documentation: [context/ARCHITECTURE.md]\n"
    ),
    "check.py": CHECK,
    ".gitignore": ".env\n",
    ".env": "AWS_SECRET_ACCESS_KEY=hunter2\n",
}


def git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "config-service"
    for path, text in FILES.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8", newline="\n")
    git(root, "init", "-q")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "Document the error contract")
    return root


@pytest.fixture
def librarian_tools(source, tmp_path):
    memory = tmp_path / "memory"
    notes, index, cache = (
        NoteStore(memory / "notes"),
        MemoryIndex(memory / "librarian.db"),
        EmbeddingCache(memory / "embeddings.db"),
    )
    notes.remember(
        title="Duplicate names map to 409 Conflict",
        statement="ErrorMiddleware maps DuplicateApplicationNameException to 409 Conflict.",
        rationale="A duplicate conflicts with existing state; it is not malformed input.",
        sources=[MIDDLEWARE, "context/ARCHITECTURE.md"],
        confidence=0.9,
    )
    build_index(source, source / "knowledge", notes, index, HashingEmbedder(), cache)
    return LibrarianTools(source, notes, index, HashingEmbedder(), cache, memory / "retrievals")


def scripted_mechanic(config: TeamConfig, *replies) -> AgentMechanic:
    model = ScriptedModel(replies=list(replies))
    return AgentMechanic(lambda: model, config.test_command, config.lint_command, config.timeout_seconds)


GOOD_REPAIR = (
    calls(call("read_file", "r", file_path=f"/workspace/{MIDDLEWARE}")),
    calls(
        call(
            "edit_file",
            "e",
            file_path=f"/workspace/{MIDDLEWARE}",
            old_string='Status400BadRequest, "Bad Request"',
            new_string='Status409Conflict, "Conflict"',
        )
    ),
    AIMessage(
        content='Restored the 409.\n```json\n{"intent": "Map duplicate application names back to 409", '
        '"rationale": "The note and the knowledge graph say 409 is the contract", '
        '"risks": []}\n```'
    ),
)


@pytest.fixture
def config(source, tmp_path):
    python = f'"{sys.executable}"'
    return TeamConfig(
        source=source,
        runs_dir=tmp_path / "runs",
        test_command=f"{python} check.py",
        lint_command=f'{python} -c "print(1)"',
        timeout_seconds=60,
        model="scripted",
        api_key="unused",
    )


def team_with(config, librarian_tools, mechanic) -> Team:
    doctor = DoctorAdapter(config.test_command, config.lint_command, config.timeout_seconds)
    return Team(
        config, doctor, LibrarianAdapter(librarian_tools), {"agent": mechanic, "human": HumanMechanic()}
    )
