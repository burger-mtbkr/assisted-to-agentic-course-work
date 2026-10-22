# agent-hub

One browser UI over every agent in this repo: chat with the PAIR Agent
(Module 6), the Doctor (Module 7) or the Librarian (Module 8), and run,
approve and inspect Codebase Team repairs (Module 9). It sits at the repo
root, beside `agent-kit/`, because it spans those modules.

## Run it

From the repo root, build the UI once (and again after changing `web/`),
then start the hub:

```bash
npm --prefix agent-hub/web install
npm --prefix agent-hub/web run build
uv run --project agent-hub agent-hub
```

Open <http://127.0.0.1:8765>. It listens on localhost only.

Each agent reads its own settings and `GEMINI_API_KEY` from its own
git-ignored `.env`, exactly as its CLI does. One that cannot start (no key,
no `knowledge.db`, no Librarian index) is listed as unavailable with the
reason; the others still run.

## What it does

- **Chats** with any chat agent: a sidebar of saved chats (search, rename,
  export, import, delete), streamed replies, tool calls shown live and
  expandable to their input and result, loaded skills named as skills, a
  Stop button, per-chat token usage, the agent's working memory, and its
  tools, skills and system prompt.
- **Model picker** per agent, offering only the free-tier models
  (`FREE_MODELS` in `pair-agent/src/pair_agent/provider.py`). Switch when a
  model's daily quota is spent (Gemini replies 429). The choice is kept in
  the git-ignored `.hub-models.json` across restarts. For the Codebase Team
  it is the Mechanic's model; its Doctor and Librarian steps call none.
- **Codebase Team runs**: start a run (optionally with a seeded
  regression), watch the steps, approve or narrow the Mechanic's edit
  boundary, then see the patch, the workspace diff, the verification and
  the coordination evals. Runs live in `codebase-team/.codebase-team-runs/`,
  as the CLI's do, so `codebase-team inspect` reads them too.
- Light, dark or system theme. Ctrl+K searches chats, Ctrl+Shift+O starts a
  new one, Esc stops a running turn.

## How a turn behaves

- A chat is saved as the agent's own conversation state in
  `agent-hub/.sessions/<id>.json` (git-ignored): the PAIR Agent's messages
  array, or a Deep Agent's LangChain messages. Resuming replays it exactly.
- A turn that fails or is stopped is rolled back whole. A new chat stopped
  before its first answer is discarded and its message returns to the
  composer.
- Stop waits for a running tool to finish (a test run, a skill script)
  rather than abandoning it in a worker thread, then ends the turn before
  the next model call.
- A turn outlives its browser tab: reload mid-turn and the chat shows it
  still working, then the answer.
- Turns of one agent run one at a time; different agents run side by side.
- Doctor and Librarian chats are recorded in each agent's own run folder
  under the chat's id, as their CLIs record sessions.
- Export writes the PAIR Agent's chats in the terminal's `/save` format, so
  `/load` reads them; other agents' chats export as `{agent, title, state}`.
  Import accepts both.

## Settings

| Variable | Default |
|---|---|
| `AGENT_HUB_PORT` | `8765` |
| `AGENT_HUB_SESSIONS_DIR` | `agent-hub/.sessions` |

## Develop the UI

`npm --prefix agent-hub/web run dev` serves the UI with hot reload on
<http://localhost:5173>, forwarding `/api` to a running hub. React 19, MUI 9,
Vite, TypeScript; `npm --prefix agent-hub/web run build` type-checks and
builds.

## Layout

```text
agent-hub/
  src/agent_hub/
    agents.py    the chat agents behind one interface: PAIR, and Deep Agents (Doctor, Librarian)
    team.py      Codebase Team runs: start, state from the trajectory, approve, continue
    sessions.py  saved chats, one JSON file each
    server.py    the HTTP API, the turn stream, and startup
  web/src/       the React app (components/, team/)
```
