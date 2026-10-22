"""The hub's HTTP side: a JSON API over the agents, their saved chats and the team's runs,
plus the built React UI.

A chat turn streams newline-delimited JSON events - token, tool_call, tool_result,
stopping, stopped, error - and ends with done, carrying the saved chat. A turn outlives its
stream: if the browser reloads mid-turn the turn still finishes and is saved, and the chat
reports `running` until it has. Turns of one agent run one at a time; different agents'
turns run side by side.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path

import uvicorn
from dotenv import dotenv_values
from pair_agent.provider import ProviderError
from pair_agent.runtime import PACKAGE_ROOT as PAIR_ROOT
from pair_agent.runtime import StartupError, open_runtime
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, PlainTextResponse, Response, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send

from agent_hub.agents import DISPLAY, PROFILES, DeepChat, PairChat, TurnStopped, doctor, librarian
from agent_hub.sessions import SessionStore, UnreadableSession, title_from
from agent_hub.team import RunBusy, TeamRuns

HUB_ROOT = Path(__file__).resolve().parents[2]  # agent-hub/
WEB_DIST = HUB_ROOT / "web" / "dist"
BUILD_HINT = (
    "The UI is not built. Run: npm --prefix agent-hub/web install && npm --prefix agent-hub/web run build"
)
ERROR_CHARS = 800

ChatAgent = PairChat | DeepChat


@dataclass
class Agents:
    chat: dict[str, ChatAgent] = field(default_factory=dict)
    team: TeamRuns | None = None
    unavailable: dict[str, str] = field(default_factory=dict)  # key -> why


@dataclass
class LiveTurn:
    stop: threading.Event = field(default_factory=threading.Event)
    events: asyncio.Queue = field(default_factory=asyncio.Queue)

    def emit(self, event: dict) -> None:
        self.events.put_nowait(event)


class RequireJson:
    """Writes must be JSON. A cross-site form or `no-cors` fetch cannot send that without
    a CORS preflight, which this server never answers."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] in ("POST", "PUT", "PATCH"):
            content_type = dict(scope["headers"]).get(b"content-type", b"")
            if not content_type.startswith(b"application/json"):
                await _error(415, "Send JSON (Content-Type: application/json).")(scope, receive, send)
                return
        await self.app(scope, receive, send)


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


async def _body(request: Request) -> dict:
    try:
        body = json.loads(await request.body() or b"{}")
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def _describe_error(exc: Exception) -> str:
    text = str(exc) if isinstance(exc, ProviderError) else f"{type(exc).__name__}: {exc}"
    return text if len(text) <= ERROR_CHARS else text[:ERROR_CHARS] + "..."


class ModelChoices:
    """The model picked for each agent, kept across restarts: a spent free-tier quota lasts
    until midnight Pacific, so a restart should not switch back to the spent model."""

    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict[str, str]:
        try:
            choices = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return choices if isinstance(choices, dict) else {}

    def apply(self, agents: Agents) -> None:
        for key, model in self.load().items():
            agent = agents.chat.get(key) or (agents.team if key == "team" else None)
            if agent and model in agent.models and model != agent.model:
                agent.set_model(model)

    def save(self, key: str, model: str) -> None:
        self.path.write_text(json.dumps({**self.load(), key: model}, indent=2), encoding="utf-8")


def create_app(
    agents: Agents, store: SessionStore, choices: ModelChoices, dist: Path = WEB_DIST
) -> Starlette:
    locks = {key: asyncio.Lock() for key in agents.chat}
    running: dict[str, LiveTurn] = {}

    def view(session: dict) -> dict:
        display = DISPLAY.get(session["agent"])
        return {
            **{key: session[key] for key in ("id", "agent", "title", "created", "updated", "usage", "state")},
            "messages": display(session["state"]) if display else [],
            "running": session["id"] in running,
        }

    def chat_agent(key: str) -> ChatAgent:
        if key not in agents.chat:
            reason = agents.unavailable.get(key)
            raise LookupError(
                f"{PROFILES[key].name} is unavailable: {reason}" if reason else f"No chat agent {key!r}."
            )
        return agents.chat[key]

    def load(session_id: str) -> dict | JSONResponse:
        try:
            return store.get(session_id)
        except KeyError:
            return _error(404, "No such chat.")
        except UnreadableSession as exc:
            return _error(422, f"This chat's file is unreadable: {exc}")

    # -- agents -------------------------------------------------------------------------

    async def list_agents(request: Request) -> Response:
        listed = []
        for key, profile in PROFILES.items():
            entry = {
                "key": key,
                "kind": profile.kind,
                "name": profile.name,
                "module": profile.module,
                "summary": profile.summary,
                "available": False,
                "reason": agents.unavailable.get(key),
            }
            agent = agents.chat.get(key) or (agents.team if key == "team" else None)
            if agent:
                entry.update(
                    available=True, reason=None, model=agent.model, models=agent.models, **agent.describe()
                )
            listed.append(entry)
        return JSONResponse(listed)

    async def set_model(request: Request) -> Response:
        key = request.path_params["key"]
        agent = agents.chat.get(key) or (agents.team if key == "team" else None)
        if agent is None:
            return _error(404, f"No agent {key!r} is running.")
        model = (await _body(request)).get("model")
        if model not in agent.models:
            return _error(400, f"Choose one of: {', '.join(agent.models)}.")
        agent.set_model(model)
        choices.save(key, model)
        return JSONResponse({"key": key, "model": model})

    # -- chats ---------------------------------------------------------------------------

    async def list_sessions(request: Request) -> Response:
        return JSONResponse([{**s, "running": s["id"] in running} for s in store.list()])

    async def create_session(request: Request) -> Response:
        try:
            agent = chat_agent(str((await _body(request)).get("agent", "")))
        except (LookupError, KeyError) as exc:
            return _error(400, str(exc))
        return JSONResponse(view(store.create(agent.profile.key)), status_code=201)

    async def import_session(request: Request) -> Response:
        body = await _body(request)
        data, name = body.get("data"), str(body.get("filename", "")).removesuffix(".json")
        if isinstance(data, list):  # a PAIR Agent conversation from the terminal's /save
            key, state, title = "pair", data, name
        elif isinstance(data, dict):  # a chat exported from this hub
            key, state, title = str(data.get("agent", "")), data.get("state"), str(data.get("title") or name)
        else:
            return _error(400, "Not a conversation this hub can open.")
        try:
            agent = chat_agent(key)
            state = agent.validate(state)
        except (LookupError, KeyError) as exc:
            return _error(400, f"Not a conversation this hub can open: {exc}")
        except (ValueError, TypeError, AttributeError) as exc:
            return _error(400, f"Not a saved {agent.profile.name} conversation: {exc}")
        return JSONResponse(view(store.create(agent.profile.key, title[:200], state)), status_code=201)

    async def get_session(request: Request) -> Response:
        session = load(request.path_params["id"])
        return session if isinstance(session, Response) else JSONResponse(view(session))

    async def export_session(request: Request) -> Response:
        session = load(request.path_params["id"])
        if isinstance(session, Response):
            return session
        agent = agents.chat.get(session["agent"])
        exported = (
            agent.export(session["state"])
            if isinstance(agent, PairChat)
            else {"agent": session["agent"], "title": session["title"], "state": session["state"]}
        )
        return JSONResponse(exported)

    async def rename_session(request: Request) -> Response:
        title = str((await _body(request)).get("title", "")).strip()
        if not title:
            return _error(400, "A title is required.")
        session = load(request.path_params["id"])
        if isinstance(session, Response):
            return session
        session["title"] = title[:200]
        store.save(session)
        return JSONResponse({"id": session["id"], "title": session["title"]})

    async def delete_session(request: Request) -> Response:
        session_id = request.path_params["id"]
        if session_id in running:
            return _error(409, "Stop the running turn before deleting this chat.")
        try:
            store.delete(session_id)
        except KeyError:
            return _error(404, "No such chat.")
        return Response(status_code=204)

    async def run_turn(session_id: str, agent: ChatAgent, text: str, turn: LiveTurn) -> None:
        result = None
        try:
            async with locks[agent.profile.key]:
                state = store.get(session_id)["state"]
                try:
                    result = await agent.run_turn(session_id, state, text, turn.emit, turn.stop)
                except TurnStopped:
                    turn.emit({"type": "stopped"})
        except Exception as exc:  # the agent rolled the turn back; report it and keep serving
            turn.emit({"type": "error", "message": _describe_error(exc)})
        finally:
            session = None
            try:
                session = store.get(session_id)
                if result:
                    session["state"] = result.state
                    for key, value in result.usage.items():
                        session["usage"][key] += value
                elif not session["state"]:
                    session["title"] = ""  # a first turn that was rolled back leaves no title behind
                store.save(session)
            except (KeyError, UnreadableSession) as exc:
                turn.emit({"type": "error", "message": f"Could not save the chat: {exc}"})
            running.pop(session_id, None)
            turn.emit({"type": "done", "session": session and view(session)})

    async def stream(turn: LiveTurn) -> AsyncIterator[str]:
        while True:
            event = await turn.events.get()
            yield json.dumps(event, ensure_ascii=False) + "\n"
            if event["type"] == "done":
                return

    async def post_message(request: Request) -> Response:
        session_id = request.path_params["id"]
        text = str((await _body(request)).get("text", "")).strip()
        if not text:
            return _error(400, "A message is required.")
        session = load(session_id)
        if isinstance(session, Response):
            return session
        try:
            agent = chat_agent(session["agent"])
        except LookupError as exc:
            return _error(409, str(exc))
        if session_id in running:
            return _error(409, "A turn is already running in this chat.")
        if not session["title"]:
            session["title"] = title_from(text)
            store.save(session)
        turn = running[session_id] = LiveTurn()
        asyncio.create_task(run_turn(session_id, agent, text, turn))
        return StreamingResponse(stream(turn), media_type="application/x-ndjson")

    async def stop_turn(request: Request) -> Response:
        turn = running.get(request.path_params["id"])
        if turn and not turn.stop.is_set():
            turn.stop.set()
            turn.emit({"type": "stopping"})
        return Response(status_code=204)

    # -- team runs -----------------------------------------------------------------------

    def team_or_error() -> TeamRuns | JSONResponse:
        if agents.team:
            return agents.team
        return _error(
            409, f"The Codebase Team is unavailable: {agents.unavailable.get('team', 'not started')}"
        )

    async def list_runs(request: Request) -> Response:
        team = team_or_error()
        return team if isinstance(team, Response) else JSONResponse(team.list())

    async def start_run(request: Request) -> Response:
        team = team_or_error()
        if isinstance(team, Response):
            return team
        scenario = (await _body(request)).get("scenario") or None
        try:
            return JSONResponse(await team.start(scenario), status_code=201)
        except ValueError as exc:
            return _error(400, str(exc))

    async def get_run(request: Request) -> Response:
        team = team_or_error()
        if isinstance(team, Response):
            return team
        try:
            return JSONResponse(team.detail(request.path_params["task"]))
        except FileNotFoundError:
            return _error(404, "No such run.")

    async def approve_run(request: Request) -> Response:
        team = team_or_error()
        if isinstance(team, Response):
            return team
        body = await _body(request)
        paths = body.get("paths")
        if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
            return _error(400, "paths must be a list of workspace paths.")
        try:
            return JSONResponse(
                await team.approve(
                    request.path_params["task"],
                    paths,
                    str(body.get("rationale", "")),
                    bool(body.get("allow_tests")),
                    bool(body.get("approved", True)),
                )
            )
        except FileNotFoundError:
            return _error(404, "No such run.")
        except ValueError as exc:
            return _error(400, str(exc))

    async def continue_run(request: Request) -> Response:
        team = team_or_error()
        if isinstance(team, Response):
            return team
        try:
            return JSONResponse(
                await team.proceed(request.path_params["task"], bool((await _body(request)).get("remember")))
            )
        except FileNotFoundError:
            return _error(404, "No such run.")
        except RunBusy as exc:
            return _error(409, str(exc))
        except ValueError as exc:
            return _error(400, str(exc))

    async def index(request: Request) -> Response:
        page = dist / "index.html"
        if not page.is_file():
            return PlainTextResponse(BUILD_HINT, status_code=503)
        return FileResponse(page)

    return Starlette(
        routes=[
            Route("/api/agents", list_agents),
            Route("/api/agents/{key}/model", set_model, methods=["PUT"]),
            Route("/api/sessions", list_sessions, methods=["GET"]),
            Route("/api/sessions", create_session, methods=["POST"]),
            Route("/api/sessions/import", import_session, methods=["POST"]),
            Route("/api/sessions/{id}", get_session, methods=["GET"]),
            Route("/api/sessions/{id}", rename_session, methods=["PATCH"]),
            Route("/api/sessions/{id}", delete_session, methods=["DELETE"]),
            Route("/api/sessions/{id}/export", export_session),
            Route("/api/sessions/{id}/messages", post_message, methods=["POST"]),
            Route("/api/sessions/{id}/stop", stop_turn, methods=["POST"]),
            Route("/api/team/runs", list_runs, methods=["GET"]),
            Route("/api/team/runs", start_run, methods=["POST"]),
            Route("/api/team/runs/{task}", get_run),
            Route("/api/team/runs/{task}/approve", approve_run, methods=["POST"]),
            Route("/api/team/runs/{task}/continue", continue_run, methods=["POST"]),
            Route("/", index),
            Route("/c/{id}", index),
            Route("/team", index),
            Route("/team/{task}", index),
            Mount("/assets", StaticFiles(directory=dist / "assets", check_dir=False)),
        ],
        middleware=[
            # A page on another site that rebinds its DNS name to 127.0.0.1 still sends its own Host.
            Middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"]),
            Middleware(RequireJson),
        ],
    )


async def start_agents(stack: AsyncExitStack) -> Agents:
    """Start every agent that can start; one that cannot is listed as unavailable, with why."""
    agents = Agents()
    pair_settings = {**dotenv_values(PAIR_ROOT / ".env"), **os.environ}
    try:
        agents.chat["pair"] = PairChat(await stack.enter_async_context(open_runtime(pair_settings)))
    except StartupError as exc:
        agents.unavailable["pair"] = str(exc)
    for key, build in (("doctor", doctor), ("librarian", librarian)):
        try:
            agents.chat[key] = build()
        except Exception as exc:  # a missing key, codebase or index: the other agents still run
            agents.unavailable[key] = _describe_error(exc)
    try:
        from codebase_team.cli import build_team
        from codebase_team.orchestrator import TeamConfig

        agents.team = TeamRuns(TeamConfig.load(), build_team)
    except Exception as exc:
        agents.unavailable["team"] = _describe_error(exc)
    return agents


async def serve() -> int:
    port = int(os.environ.get("AGENT_HUB_PORT", "8765"))
    sessions_dir = Path(os.environ.get("AGENT_HUB_SESSIONS_DIR") or HUB_ROOT / ".sessions").resolve()
    choices = ModelChoices(HUB_ROOT / ".hub-models.json")
    async with AsyncExitStack() as stack:
        agents = await start_agents(stack)
        choices.apply(agents)
        for key, profile in PROFILES.items():
            if key in agents.unavailable:
                print(f"  {profile.name}: unavailable - {agents.unavailable[key]}")
            else:
                agent = agents.chat.get(key) or agents.team
                print(f"  {profile.name}: ready ({agent.model})")
        if not (WEB_DIST / "index.html").is_file():
            print(f"[warning] {BUILD_HINT}", file=sys.stderr)
        print(f"Chats saved in {sessions_dir}")
        print(f"Open http://127.0.0.1:{port} - Ctrl+C to stop", flush=True)
        config = uvicorn.Config(
            create_app(agents, SessionStore(sessions_dir), choices),
            host="127.0.0.1",
            port=port,
            log_level="warning",
        )
        await uvicorn.Server(config).serve()
    return 0


def main() -> None:
    for stream in (sys.stdout, sys.stderr):  # Windows consoles default to cp1252
        stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(asyncio.run(serve()))
