"""A small git-tracked codebase with a knowledge graph, and a Librarian config over it."""

import json
import subprocess
from pathlib import Path

import pytest

from librarian_agent.config import LibrarianConfig
from librarian_agent.embeddings import HashingEmbedder
from librarian_agent.indexer import build_index
from librarian_agent.notes import NoteStore
from librarian_agent.store import EmbeddingCache, MemoryIndex

PROJECT_ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "context/ARCHITECTURE.md": (
        "# Architecture\n\n## Error handling\n\nErrorMiddleware maps duplicate names to 409 Conflict and "
        "validation failures to 400.\n\n## Data access\n\nReads scan the table and cache the result.\n"
    ),
    "src/Api/Middleware/ErrorMiddleware.cs": (
        "public class ErrorMiddleware {\n  // DuplicateNameException -> 409 Conflict\n}\n"
    ),
    "src/Api.UnitTests/Middleware/ErrorMiddlewareTests.cs": (
        "public class ErrorMiddlewareTests {\n  // DuplicateName_MapsTo409\n}\n"
    ),
    "src/Api/Models/Flag.cs": "public class Flag { public bool Enabled; }\n",
    "ui/src/api.ts": "export async function listFlags() {}\n",
    "ui/src/api.test.ts": "test('listFlags', () => {});\n",
    "package-lock.json": "{}\n",
    "knowledge/nodes/terms.yaml": (
        "nodes:\n"
        "  - id: error_response\n    type: domain_term\n    area: api\n    name: ErrorResponse\n"
        "    definition: The JSON error body.\n    aliases: [error body]\n"
        "    warnings: [Duplicates are 409.]\n"
        "    source_files: [src/Api/Middleware/ErrorMiddleware.cs]\n"
        "    documentation: [context/ARCHITECTURE.md]\n"
        "  - id: feature_flag\n    type: domain_term\n    area: flags\n    name: FeatureFlag\n"
        "    definition: A boolean switch.\n    aliases: [flag]\n"
        "    source_files: [src/Api/Models/Flag.cs]\n"
    ),
    "knowledge/edges/edges.yaml": (
        "edges:\n  - from: feature_flag\n    to: error_response\n    relationship: duplicate_returns\n"
    ),
    ".gitignore": ".env\n",
    ".env": "AWS_SECRET_ACCESS_KEY=hunter2\n",
}


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.email=t@example.com", "-c", "user.name=Tester", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


@pytest.fixture
def codebase(tmp_path):
    root = tmp_path / "codebase"
    for path, text in FILES.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", "context", "knowledge", ".gitignore")
    git(root, "commit", "-q", "-m", "Document the error contract")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "Add ErrorMiddleware and flags")
    return root


@pytest.fixture
def config(codebase, tmp_path):
    return LibrarianConfig(
        codebase_path=codebase,
        knowledge_dir=codebase / "knowledge",
        memory_dir=tmp_path / "memory",
        skills_dir=PROJECT_ROOT / "skills",
        model="scripted",
        api_key="unused",
        embeddings="hashing",
        embedding_model="unused",
    )


@pytest.fixture
def notes(config):
    return NoteStore(config.notes_dir)


@pytest.fixture
def index(config, notes):
    index = MemoryIndex(config.db_path)
    build_index(
        config.codebase_path,
        config.knowledge_dir,
        notes,
        index,
        HashingEmbedder(),
        EmbeddingCache(config.cache_path),
    )
    return index
