"""Curated indexing: which files, how they are chunked, which edges, and the embedding cache."""

import pytest

from librarian_agent.embeddings import HashingEmbedder
from librarian_agent.indexer import build_index, chunk_lines, indexable, kind_of, tested_in_edges
from librarian_agent.store import Edge, IndexUnavailable, MemoryIndex


@pytest.mark.parametrize(
    ("path", "kind"),
    [
        ("context/ARCHITECTURE.md", "doc"),
        ("knowledge/nodes/terms.yaml", "knowledge"),
        ("openapi.json", "contract"),
        ("src/Api/appsettings.Development.json", "config"),
        ("src/Api.UnitTests/Middleware/ErrorMiddlewareTests.cs", "test"),
        ("ui/src/api.test.ts", "test"),
        ("src/Api/Middleware/ErrorMiddleware.cs", "source"),
    ],
)
def test_kind_of(path, kind):
    assert kind_of(path) == kind


def test_only_explanatory_files_are_indexed():
    assert all(
        map(indexable, ["README.md", "src/A.cs", "ui/src/a.ts", "openapi.json", "src/appsettings.json"])
    )
    assert not any(
        map(indexable, ["package-lock.json", "src/Api.csproj", "ui/src/vite-env.d.ts", "global.json"])
    )


def test_markdown_chunks_at_headings_and_code_in_overlapping_windows():
    doc = ["# A", "text", "## B", "more", "more"]
    assert list(chunk_lines(doc, markdown=True)) == [(1, 2), (3, 5)]
    code = [f"line {i}" for i in range(130)]
    assert list(chunk_lines(code, markdown=False)) == [(1, 60), (51, 110), (101, 130)]


def test_tests_are_linked_to_what_they_test_by_naming_convention():
    paths = [
        "src/Api/Middleware/ErrorMiddleware.cs",
        "src/Api.UnitTests/Middleware/ErrorMiddlewareTests.cs",
        "ui/src/api.ts",
        "ui/src/api.test.ts",
        "src/Api/Models/Flag.cs",
    ]
    assert tested_in_edges(paths) == [
        Edge(
            "file:src/Api/Middleware/ErrorMiddleware.cs",
            "tested_in",
            "file:src/Api.UnitTests/Middleware/ErrorMiddlewareTests.cs",
            "naming convention: ErrorMiddlewareTests.cs",
            0.9,
        ),
        Edge(
            "file:ui/src/api.ts",
            "tested_in",
            "file:ui/src/api.test.ts",
            "naming convention: api.test.ts",
            0.9,
        ),
    ]


def test_the_index_covers_visible_files_the_graph_and_never_secrets(index, config):
    stats = index.stats()
    assert stats["embedder"] == "hashing-512" and stats["documents"] == 8
    assert stats["entities_by_kind"] == {"area": 2, "file": 8, "term": 2}
    assert stats["relationships_by_type"] == {
        "contains": 2,
        "documents": 1,
        "duplicate_returns": 1,
        "implemented_in": 2,
        "tested_in": 2,
    }
    assert ".env" not in index.documents() and "package-lock.json" not in index.documents()
    texts = [chunk.text for _, chunk in index.search(HashingEmbedder().embed_query("secret"))]
    assert not any("hunter2" in t for t in texts)


def test_a_different_embedder_cannot_query_the_index(index):
    with pytest.raises(IndexUnavailable, match="built with hashing-512"):
        index.require("gemini-embedding-001-768")
    with pytest.raises(IndexUnavailable, match="No index yet"):
        MemoryIndex(index.db_path.with_name("none.db")).require("hashing-512")


class CountingEmbedder(HashingEmbedder):
    def __init__(self):
        super().__init__()
        self.embedded = 0

    def embed_documents(self, texts):
        self.embedded += len(texts)
        return super().embed_documents(texts)


def test_rebuilding_reembeds_only_what_changed(config, notes, index):
    counting = CountingEmbedder()
    build_index(config.codebase_path, config.knowledge_dir, notes, index, counting)
    assert counting.embedded == 0  # every chunk was already in the cache
    (config.codebase_path / "src/Api/Models/Flag.cs").write_text(
        "public class Flag { int X; }\n", encoding="utf-8"
    )
    build_index(config.codebase_path, config.knowledge_dir, notes, index, counting)
    assert counting.embedded == 1
