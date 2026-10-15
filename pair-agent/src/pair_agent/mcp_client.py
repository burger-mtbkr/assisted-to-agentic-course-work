"""Client side of MCP: read mcp.json, start each server, discover and call its tools."""

from __future__ import annotations

import json
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import StdioServerParameters
from mcp.client import Client

from pair_agent.tools import Tool, ToolOutcome


class McpConfigError(Exception):
    """mcp.json is missing, malformed, or a server in it would not start."""


def load_server_params(config_path: Path) -> dict[str, StdioServerParameters]:
    if not config_path.is_file():
        raise McpConfigError(f"MCP config not found: {config_path}")
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise McpConfigError(f"{config_path} is not valid JSON: {exc}") from exc
    servers = config.get("mcpServers")
    if not isinstance(servers, dict) or not servers:
        raise McpConfigError(f"{config_path} has no \"mcpServers\" entries")

    params = {}
    for name, entry in servers.items():
        if "command" not in entry:
            raise McpConfigError(f"MCP server '{name}' in {config_path} has no \"command\"")
        cwd = entry.get("cwd")
        params[name] = StdioServerParameters(
            command=entry["command"],
            args=entry.get("args", []),
            env=entry.get("env"),
            cwd=(config_path.parent / cwd).resolve() if cwd else None,
        )
    return params


def _result_text(result) -> str:
    return "\n".join(block.text for block in result.content if getattr(block, "text", None) is not None)


class McpConnections:
    """Holds one live client session per configured server for the harness's lifetime."""

    def __init__(self) -> None:
        self._stack = AsyncExitStack()
        self.tools: list[Tool] = []
        self.instructions: dict[str, str] = {}

    async def start(self, config_path: Path) -> None:
        for server, params in load_server_params(config_path).items():
            try:
                client = await self._stack.enter_async_context(Client(params))
                listed = (await client.list_tools()).tools
                self.instructions[server] = client.instructions or ""
            except Exception as exc:
                raise McpConfigError(
                    f"MCP server '{server}' failed to start ({params.command} "
                    f"{' '.join(params.args)}): {type(exc).__name__}: {exc}"
                ) from exc
            for tool in listed:
                self.tools.append(Tool(
                    name=f"mcp__{server}__{tool.name}",
                    description=tool.description or "",
                    input_schema=tool.input_schema,
                    handler=self._caller(client, tool.name),
                    source=f"mcp:{server}",
                ))

    @staticmethod
    def _caller(client: Client, tool_name: str):
        async def call(**arguments) -> ToolOutcome:
            result = await client.call_tool(tool_name, arguments)
            return ToolOutcome(_result_text(result), bool(result.is_error))
        return call

    async def close(self) -> None:
        await self._stack.aclose()
