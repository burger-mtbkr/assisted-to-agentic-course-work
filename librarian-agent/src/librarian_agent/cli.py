"""`librarian`: talk to the Librarian, or build, seed, query and inspect its memory directly."""

from __future__ import annotations

import argparse
import json
import sys

from agent_kit.console import converse
from agent_kit.recording import RunRecorder

from librarian_agent.agent import LibrarianAgent, build_embedder, build_tools
from librarian_agent.config import ConfigError, LibrarianConfig
from librarian_agent.indexer import build_index
from librarian_agent.inspection import report, retrieval_artifact
from librarian_agent.notes import NoteError, NoteStore
from librarian_agent.seeds import seed
from librarian_agent.store import EmbeddingCache, IndexUnavailable, MemoryIndex


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="librarian", description="The Librarian: memory and retrieval.")
    commands = parser.add_subparsers(dest="command")
    chat = commands.add_parser("chat", help="converse (the default)")
    chat.add_argument("--ask", action="append", metavar="MESSAGE", help="send MESSAGE and exit; repeatable")
    commands.add_parser("index", help="rebuild the derived index from the codebase and the notes")
    commands.add_parser("seed", help="write the starter decision notes (skips existing ones)")
    retrieve = commands.add_parser("retrieve", help="run hybrid retrieval with no chat model")
    retrieve.add_argument("query")
    retrieve.add_argument("--include-superseded", action="store_true")
    inspect = commands.add_parser("inspect", help="notes, index, retrievals and sessions at a glance")
    inspect.add_argument("--note", metavar="ID", help="print one note in full")
    inspect.add_argument("--retrievals", type=int, default=5, metavar="N")
    inspect.add_argument(
        "--retrieval", metavar="ARTIFACT", help='print one retrieval artifact (name or "latest")'
    )
    args = parser.parse_args(argv)

    try:
        config = LibrarianConfig.load()
        if args.command == "inspect":
            if args.note:
                print(NoteStore(config.notes_dir).read(args.note).to_markdown())
            elif args.retrieval:
                print(retrieval_artifact(config, args.retrieval))
            else:
                print(report(config, args.retrievals))
            return 0
        if args.command == "seed":
            for note in seed(NoteStore(config.notes_dir)):
                print(f"wrote notes/{note.id}.md")
            print("Run `librarian index` so the notes are searchable.")
            return 0
        embedder = build_embedder(config)
        if args.command == "index":
            built = build_index(
                config.codebase_path,
                config.knowledge_dir,
                NoteStore(config.notes_dir),
                MemoryIndex(config.db_path),
                embedder,
                EmbeddingCache(config.cache_path),
            )
            print(
                f"Indexed {built.documents} files as {built.chunks} chunks, {built.notes} notes, "
                f"{built.entities} entities, {built.relationships} relationships ({embedder.name})."
            )
            return 0
        if args.command == "retrieve":
            result = build_tools(config, embedder).retrieve_context(args.query, args.include_superseded)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        config.require_key()  # the chat model needs it even when embeddings are local
    except (ConfigError, NoteError, IndexUnavailable) as exc:
        print(f"librarian: {exc}", file=sys.stderr)
        return 2

    print(f"Librarian ({config.model}, {embedder.name}) over {config.codebase_path}")
    print(f"Memory in {config.memory_dir}\n")
    return converse(
        "Librarian",
        lambda: LibrarianAgent(config, RunRecorder(config.memory_dir), embedder),
        getattr(args, "ask", None),
    )


if __name__ == "__main__":
    sys.exit(main())
