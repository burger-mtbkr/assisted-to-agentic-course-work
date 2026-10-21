"""The Librarian, assembled on Deep Agents with agent-kit.

Read-only over the codebase like the Doctor, but with memory of its own: notes it
can write, an index it searches, and Git it reads.
"""

from __future__ import annotations

from agent_kit.harness import Session, assemble, gemini
from agent_kit.mount import GitScopedBackend
from agent_kit.recording import RunRecorder
from deepagents import FilesystemPermission
from deepagents.backends import FilesystemBackend
from langchain_core.language_models import BaseChatModel

from librarian_agent.config import LibrarianConfig
from librarian_agent.embeddings import Embedder, GeminiEmbedder, HashingEmbedder
from librarian_agent.notes import NoteStore
from librarian_agent.prompts import SYSTEM_PROMPT
from librarian_agent.store import EmbeddingCache, MemoryIndex
from librarian_agent.tools import LibrarianTools

# No filesystem writes of any kind: notes go through remember_decision only.
EXCLUDED_TOOLS = frozenset({"write_file", "edit_file", "delete", "execute", "write_todos", "task"})


def build_embedder(config: LibrarianConfig) -> Embedder:
    if config.embeddings == "gemini":
        return GeminiEmbedder(config.require_key(), config.embedding_model)
    return HashingEmbedder()


def build_tools(config: LibrarianConfig, embedder: Embedder) -> LibrarianTools:
    return LibrarianTools(
        config.codebase_path,
        NoteStore(config.notes_dir),
        MemoryIndex(config.db_path),
        embedder,
        EmbeddingCache(config.cache_path),
        config.retrievals_dir,
    )


class LibrarianAgent(Session):
    def __init__(
        self,
        config: LibrarianConfig,
        recorder: RunRecorder,
        embedder: Embedder,
        model: BaseChatModel | None = None,
    ):
        self.tools = build_tools(config, embedder)
        graph = assemble(
            model or gemini(config.model, config.require_key()),
            system_prompt=SYSTEM_PROMPT,
            tools=self.tools.as_langchain_tools(),
            routes={
                "/codebase/": GitScopedBackend(config.codebase_path),
                "/skills/": FilesystemBackend(config.skills_dir, virtual_mode=True),
            },
            excluded_tools=EXCLUDED_TOOLS,
            permissions=[FilesystemPermission(operations=["write"], paths=["/**"], mode="deny")],
        )
        super().__init__(graph, recorder)
