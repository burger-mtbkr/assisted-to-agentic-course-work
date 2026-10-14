"""End to end through the MCP protocol (in-memory client) against the real
knowledge-graph CLI and the repo-owned graph in config-service/knowledge/.

Skipped when the CLI is absent: it ships in the git-ignored Module 5
curriculum zip.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from mcp.client import Client

from domain_lang_mcp.server import build_server

REPO = Path(__file__).resolve().parents[2]
KG_PROJECT_DIR = REPO / "modules/assisted-to-agentic-module-5/examples/knowledge-graph"
KNOWLEDGE_DIR = REPO / "config-service/knowledge"

pytestmark = pytest.mark.skipif(
    not KG_PROJECT_DIR.is_dir() or shutil.which("uv") is None,
    reason="knowledge-graph CLI (Module 5 curriculum) or uv not available",
)


@pytest.fixture(scope="session")
def knowledge_db(tmp_path_factory) -> Path:
    """Import the repo-owned YAML into a throwaway db, so tests never touch the real one."""
    db = tmp_path_factory.mktemp("kg") / "knowledge.db"
    subprocess.run(
        ["uv", "run", "--quiet", "knowledge-graph", "import",
         "--knowledge-dir", str(KNOWLEDGE_DIR), "--db", str(db)],
        cwd=KG_PROJECT_DIR, check=True, capture_output=True,
    )
    return db


@pytest.fixture
def kg_env(monkeypatch, knowledge_db):
    monkeypatch.setenv("KG_PROJECT_DIR", str(KG_PROJECT_DIR))
    monkeypatch.setenv("KG_DB", str(knowledge_db))


async def call(name: str, args: dict | None = None):
    async with Client(build_server()) as client:
        result = await client.call_tool(name, args or {})
    return result.is_error, result.content[0].text


async def test_all_five_tools_are_listed_and_read_only():
    async with Client(build_server()) as client:
        tools = (await client.list_tools()).tools
    assert {t.name for t in tools} == {
        "ping", "lookup_term", "get_related_terms", "list_domain_areas", "validate_knowledge_graph",
    }
    assert all(t.annotations.read_only_hint for t in tools)
    assert all(len(t.description) > 80 for t in tools)


async def test_ping():
    assert await call("ping", {"message": "hello"}) == (False, "Pong: hello")


async def test_ping_without_message_is_rejected_by_schema():
    is_error, text = await call("ping")
    assert is_error and "message" in text


async def test_lookup_configuration_item(kg_env):
    is_error, text = await call("lookup_term", {"term": "ConfigurationItem"})
    node = json.loads(text)
    assert not is_error
    assert node["id"] == "configuration_item"
    assert "src/ConfigApi.Service/Models/Configurations/Configuration.cs" in node["source_files"]


async def test_lookup_resolves_aliases(kg_env):
    _, text = await call("lookup_term", {"term": "config entry"})
    assert json.loads(text)["id"] == "configuration_item"


async def test_lookup_unknown_term_is_a_clean_not_found(kg_env):
    assert await call("lookup_term", {"term": "nonsense"}) == (
        False,
        json.dumps({"error": "not_found", "term": "nonsense"}),
    )


async def test_option_like_term_is_looked_up_not_parsed(kg_env):
    is_error, text = await call("lookup_term", {"term": "--help"})
    assert not is_error
    assert json.loads(text) == {"error": "not_found", "term": "--help"}


@pytest.mark.parametrize("args", [{}, {"term": ""}, {"term": "   "}])
async def test_missing_or_blank_term_is_rejected_by_schema(kg_env, args):
    is_error, text = await call("lookup_term", args)
    assert is_error and "term" in text


async def test_related_terms_for_feature_flag(kg_env):
    is_error, text = await call("get_related_terms", {"term": "feature_flag"})
    edges = json.loads(text)
    assert not is_error and len(edges) >= 3
    assert {"from": "feature_flag", "to": "application", "relationship": "scoped_to"} in edges


async def test_list_domain_areas(kg_env):
    assert await call("list_domain_areas") == (False, json.dumps(["config_service", "feature_flags"]))


async def test_validate_knowledge_graph(kg_env):
    assert await call("validate_knowledge_graph") == (False, json.dumps({"valid": True, "issues": []}))


async def test_unreachable_backend_is_an_informative_tool_error(monkeypatch, tmp_path):
    monkeypatch.setenv("KG_PROJECT_DIR", str(tmp_path / "nowhere"))
    monkeypatch.delenv("KG_DB", raising=False)
    is_error, text = await call("lookup_term", {"term": "ConfigurationItem"})
    payload = json.loads(text)
    assert is_error
    assert payload["error"] == "service_error" and payload["reason"] == "backend_unreachable"
    assert payload["fix"]


async def test_missing_db_is_an_informative_tool_error(monkeypatch, tmp_path):
    monkeypatch.setenv("KG_PROJECT_DIR", str(KG_PROJECT_DIR))
    monkeypatch.setenv("KG_DB", str(tmp_path / "missing.db"))
    is_error, text = await call("validate_knowledge_graph")
    assert is_error and json.loads(text)["reason"] == "knowledge_db_missing"
    assert not (tmp_path / "missing.db").exists()
