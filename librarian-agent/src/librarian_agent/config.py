"""Settings, from `librarian-agent/.env` and the environment (the environment wins)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EMBEDDERS = ("gemini", "hashing")


class ConfigError(Exception):
    """A setting is missing or points somewhere that does not exist."""


@dataclass(frozen=True)
class LibrarianConfig:
    codebase_path: Path
    knowledge_dir: Path
    memory_dir: Path
    skills_dir: Path
    model: str
    api_key: str
    embeddings: str
    embedding_model: str

    @property
    def notes_dir(self) -> Path:
        return self.memory_dir / "notes"

    @property
    def db_path(self) -> Path:
        return self.memory_dir / "librarian.db"

    @property
    def retrievals_dir(self) -> Path:
        return self.memory_dir / "retrievals"

    def require_key(self) -> str:
        if not self.api_key:
            raise ConfigError("GEMINI_API_KEY is not set: copy .env.example to .env and add the key.")
        return self.api_key

    @classmethod
    def load(cls, project_root: Path = PROJECT_ROOT) -> LibrarianConfig:
        # dotenv_values, not load_dotenv: the key stays out of os.environ, which
        # the git subprocesses inherit.
        settings = {**dotenv_values(project_root / ".env"), **os.environ}

        def get(name: str, default: str) -> str:
            return (settings.get(name) or default).strip()

        def path(name: str, default: str) -> Path:
            value = Path(get(name, default)).expanduser()
            return (value if value.is_absolute() else project_root / value).resolve()

        codebase = path("LIBRARIAN_CODEBASE_PATH", "../config-service")
        if not codebase.is_dir():
            raise ConfigError(f"Codebase not found at {codebase}. Set LIBRARIAN_CODEBASE_PATH.")
        embeddings = get("LIBRARIAN_EMBEDDINGS", "gemini")
        if embeddings not in EMBEDDERS:
            raise ConfigError(
                f"LIBRARIAN_EMBEDDINGS must be one of {', '.join(EMBEDDERS)}, not {embeddings!r}."
            )
        return cls(
            codebase_path=codebase,
            knowledge_dir=path("LIBRARIAN_KNOWLEDGE_DIR", str(codebase / "knowledge")),
            memory_dir=path("LIBRARIAN_MEMORY_DIR", ".librarian-memory"),
            skills_dir=project_root / "skills",
            model=get("GEMINI_MODEL", "gemini-flash-latest"),
            api_key=get("GEMINI_API_KEY", ""),
            embeddings=embeddings,
            embedding_model=get("LIBRARIAN_EMBEDDING_MODEL", "gemini-embedding-001"),
        )
