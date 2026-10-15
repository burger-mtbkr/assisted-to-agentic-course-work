"""mcp.json loading, and discovery + invocation against the real Module 5 server."""

import json
import shutil
from pathlib import Path

import pytest

from pair_agent.mcp_client import McpConfigError, McpConnections, load_server_params

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO = PACKAGE_ROOT.parent


def write(tmp_path, payload) -> Path:
    path = tmp_path / "mcp.json"
    path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
    return path


@pytest.mark.parametrize("payload, message", [
    ("{not json", "not valid JSON"),
    ({"servers": {}}, "no \"mcpServers\""),
    ({"mcpServers": {"x": {"args": []}}}, "has no \"command\""),
])
def test_bad_config_fails_clearly(tmp_path, payload, message):
    with pytest.raises(McpConfigError, match=message):
        load_server_params(write(tmp_path, payload))


def test_missing_config_fails_clearly(tmp_path):
    with pytest.raises(McpConfigError, match="MCP config not found"):
        load_server_params(tmp_path / "mcp.json")


def test_cwd_resolves_relative_to_the_config_file(tmp_path):
    params = load_server_params(write(tmp_path, {"mcpServers": {"x": {"command": "c", "cwd": ".."}}}))
    assert Path(params["x"].cwd) == tmp_path.parent.resolve()


async def test_server_that_will_not_start_names_itself(tmp_path):
    connections = McpConnections()
    try:
        with pytest.raises(McpConfigError, match="'broken' failed to start"):
            await connections.start(write(tmp_path, {"mcpServers": {"broken": {"command": "no-such-binary-xyz"}}}))
    finally:
        await connections.close()


@pytest.mark.skipif(
    not (REPO / "config-service/knowledge/knowledge.db").is_file() or shutil.which("uv") is None,
    reason="needs the built knowledge.db and the Module 5 curriculum CLI",
)
async def test_domain_lang_tools_are_discovered_and_callable_from_the_real_mcp_json():
    connections = McpConnections()
    try:
        await connections.start(PACKAGE_ROOT / "mcp.json")
        tools = {t.name: t for t in connections.tools}
        assert "mcp__domain-lang__lookup_term" in tools
        assert all(t.source == "mcp:domain-lang" for t in tools.values())
        assert connections.instructions["domain-lang"]
        found = await tools["mcp__domain-lang__lookup_term"].handler(term="feature flag")
        assert not found.is_error and json.loads(found.content)["id"] == "feature_flag"
        missing = await tools["mcp__domain-lang__lookup_term"].handler(term="nonsense")
        assert json.loads(missing.content) == {"error": "not_found", "term": "nonsense"}
    finally:
        await connections.close()
