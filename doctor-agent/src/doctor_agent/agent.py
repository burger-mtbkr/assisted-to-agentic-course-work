"""The Doctor, assembled on LangChain Deep Agents.

Deep Agents supplies the loop, tool dispatch, the filesystem tools and skill loading;
`agent-kit` the model wiring, the git-scoped mount and the turn recording. What makes
this the Doctor: its identity (prompts.py), its sensors (tools.py), its procedure
(skills/) and its boundary - read-only, everywhere.
"""

from __future__ import annotations

from agent_kit.harness import Session, assemble, gemini
from agent_kit.mount import GitScopedBackend
from agent_kit.recording import RunRecorder
from deepagents import FilesystemPermission
from deepagents.backends import FilesystemBackend
from langchain_core.language_models import BaseChatModel

from doctor_agent.config import DoctorConfig
from doctor_agent.prompts import SYSTEM_PROMPT
from doctor_agent.tools import DiagnosticTools

# Built-ins the Doctor is never offered. What remains: ls, read_file, glob, grep.
EXCLUDED_TOOLS = frozenset({"write_file", "edit_file", "delete", "execute", "write_todos", "task"})


class DoctorAgent(Session):
    def __init__(self, config: DoctorConfig, recorder: RunRecorder, model: BaseChatModel | None = None):
        tools = DiagnosticTools(
            config.codebase_path, config.test_command, config.lint_command, config.command_timeout_seconds
        )
        graph = assemble(
            model or gemini(config.model, config.api_key),
            system_prompt=SYSTEM_PROMPT,
            tools=tools.as_langchain_tools(),
            routes={
                "/codebase/": GitScopedBackend(config.codebase_path),
                "/skills/": FilesystemBackend(config.skills_dir, virtual_mode=True),
            },
            excluded_tools=EXCLUDED_TOOLS,
            permissions=[FilesystemPermission(operations=["write"], paths=["/**"], mode="deny")],
        )
        super().__init__(graph, recorder)
