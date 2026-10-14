"""Stdio MCP server exposing config-service's domain language."""

from __future__ import annotations

import json
from collections.abc import Awaitable
from typing import Annotated

import anyio
from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import Field

from domain_lang_mcp import kg

Term = Annotated[
    str,
    Field(
        min_length=1,
        max_length=200,
        pattern=r"\S",
        description=(
            "A domain term's id (configuration_item), display name (ConfigurationItem) "
            "or alias (config entry). Case-insensitive."
        ),
    ),
]

READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)


def _text(payload: object, is_error: bool = False) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))],
        is_error=is_error,
    )


async def _answer(query: Awaitable[object]) -> CallToolResult:
    """not_found is a normal answer; only a backend failure is a tool error."""
    try:
        return _text(await query)
    except kg.KgServiceError as exc:
        return _text(exc.to_payload(), is_error=True)


def build_server() -> MCPServer:
    server = MCPServer(
        "domain-lang",
        instructions=(
            "Authoritative domain language for the config-service codebase (C#/.NET, "
            "DynamoDB). Prefer lookup_term over general knowledge for any domain concept."
        ),
    )

    @server.tool(
        name="ping",
        description=(
            "Connectivity check for the domain-lang MCP server only. Echoes the message "
            "back as 'Pong: <message>'. Use it to confirm this server is reachable; it does "
            "not touch the knowledge graph, so use validate_knowledge_graph to check that."
        ),
        annotations=READ_ONLY,
        structured_output=False,
    )
    async def ping(message: Annotated[str, Field(description="Text to echo back.")]) -> str:
        return f"Pong: {message}"

    @server.tool(
        name="lookup_term",
        description=(
            "Look up what a domain term means in the config-service codebase: definition, "
            "aliases, warnings, the source files that implement it, and the docs that "
            "describe it. Accepts an id, display name or alias, case-insensitive. Use this "
            "whenever the user names a domain concept (Application, ConfigurationItem, "
            "FeatureFlag, FlagKey, ScanCache, ErrorResponse, ...) before searching code or "
            "answering from general knowledge - this repo's meanings and file names differ "
            "from common conventions. Returns {\"error\": \"not_found\"} for unknown terms."
        ),
        annotations=READ_ONLY,
    )
    async def lookup_term(term: Term) -> CallToolResult:
        return await _answer(kg.query_json(kg.KgSettings.from_env(), "lookup", term))

    @server.tool(
        name="get_related_terms",
        description=(
            "List the outgoing relationships of a config-service domain term as "
            "{from, to, relationship} records, e.g. FeatureFlag scoped_to Application. Use "
            "after lookup_term when you need adjacent concepts: what else a change touches, "
            "or which terms are easily confused with this one (not_equivalent_to). Only "
            "edges from the term are returned; [] means it has none."
        ),
        annotations=READ_ONLY,
    )
    async def get_related_terms(term: Term) -> CallToolResult:
        return await _answer(kg.query_json(kg.KgSettings.from_env(), "related", term))

    @server.tool(
        name="list_domain_areas",
        description=(
            "List the domain areas the config-service knowledge graph is partitioned into, "
            "as a JSON array of strings. Use for orientation when you do not yet know which "
            "part of the domain a question belongs to."
        ),
        annotations=READ_ONLY,
    )
    async def list_domain_areas() -> CallToolResult:
        return await _answer(kg.query_json(kg.KgSettings.from_env(), "list-areas"))

    @server.tool(
        name="validate_knowledge_graph",
        description=(
            "Check the config-service knowledge graph for integrity problems (edges that "
            "reference terms that do not exist). Returns {valid, issues}. Use after the YAML "
            "in config-service/knowledge/ is edited and re-imported, or when other tools "
            "return surprising not_found results."
        ),
        annotations=READ_ONLY,
    )
    async def validate_knowledge_graph() -> CallToolResult:
        return await _answer(kg.validate(kg.KgSettings.from_env()))

    return server


def main() -> None:
    anyio.run(build_server().run_stdio_async)
