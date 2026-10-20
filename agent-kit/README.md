# agent-kit

The plumbing the Phase 3 specialists share - the Module 7 Doctor
(`doctor-agent/`), the Module 8 Librarian (`librarian-agent/`) and the Module 9
team (`codebase-team/`). Each specialist keeps what makes it that specialist:
its system prompt, its own tools, its skills and its mounts. Everything else is
here, once.

| Module | What it is |
|---|---|
| `mount.py` | `GitScopedBackend`: a read-only Deep Agents filesystem backend that shows an agent only the files git tracks or would track, so `.env` secrets, `node_modules` and `bin/obj` never reach a model. A file reached through a symlink or a Windows junction is not visible, so a link cannot smuggle an ignored or outside file in. When the enclosing repo ignores the root itself (a curriculum fixture), the root's own `.gitignore` files decide, plus a safety net (`.env*`, dependency, build and cache directories). |
| `harness.py` | `gemini()` for the free-tier model. `model_retry()` retries 5xx overloads and per-minute 429s around every streamed model call, but not a spent per-day quota. `ToolSurface` removes tools from what one agent's model is offered and refuses them if named anyway - per agent, because Deep Agents' own harness profiles live in a process-wide registry that unions exclusions. `assemble()` builds a Deep Agent with skills under `/skills/` and only the given mounts. `Session` runs a conversation turn by turn, streams token and tool events, and records each turn, counting only the model and tools nodes' messages as new. |
| `recording.py` | `RunRecorder`: per-session `conversations/*.jsonl` and `traces/*.jsonl`. `compact()` keeps the head and tail of long output. |
| `console.py` | the terminal side of a `Session`: streamed tool progress, `--ask`-style scripted conversations, and a REPL (`/artifacts`, `/reset`, `/quit`) that survives a failed or interrupted turn. |
| `testing.py` | `ScriptedModel`, a chat model that replies from a script and records which tools it was offered, so an assembled agent is testable without a provider. |

## Tests

```bash
uv run --project agent-kit pytest agent-kit
uv run --project agent-kit ruff check agent-kit
```
