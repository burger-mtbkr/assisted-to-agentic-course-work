import DataObjectRoundedIcon from '@mui/icons-material/DataObjectRounded';
import EditSquareIcon from '@mui/icons-material/EditSquare';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import ViewSidebarOutlinedIcon from '@mui/icons-material/ViewSidebarOutlined';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import CssBaseline from '@mui/material/CssBaseline';
import Drawer from '@mui/material/Drawer';
import IconButton from '@mui/material/IconButton';
import Snackbar from '@mui/material/Snackbar';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import { ThemeProvider } from '@mui/material/styles';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AgentAvatar } from './agentLook';
import { api, streamTurn } from './api';
import { ChatView } from './components/ChatView';
import { AgentDialog, DeleteDialog, MemoryDialog, RenameDialog } from './components/Dialogs';
import { NewChat } from './components/NewChat';
import { ModelPicker, ThemeMenu } from './components/Pickers';
import { SIDEBAR_WIDTH, Sidebar } from './components/Sidebar';
import { downloadJson, formatTokens, slug } from './format';
import { TeamView } from './team/TeamView';
import { type Mode, type ModePreference, makeTheme } from './theme';
import type { AgentInfo, AgentKey, Chat, ChatSummary, LiveTurn, TurnEvent } from './types';

type Route = { kind: 'new' } | { kind: 'chat'; id: string } | { kind: 'team'; task: string | null };

const NEW_DRAFT = 'new';

function parseRoute(): Route {
  const path = window.location.pathname;
  const chat = path.match(/^\/c\/([0-9a-f]{32})$/);
  if (chat) return { kind: 'chat', id: chat[1] };
  const team = path.match(/^\/team(?:\/(task-[0-9a-f-]+))?$/);
  if (team) return { kind: 'team', task: team[1] ?? null };
  return { kind: 'new' };
}

function pathOf(route: Route): string {
  if (route.kind === 'chat') return `/c/${route.id}`;
  if (route.kind === 'team') return route.task ? `/team/${route.task}` : '/team';
  return '/';
}

function stored<T extends string>(key: string, allowed: readonly T[], fallback: T): T {
  try {
    const value = localStorage.getItem(key);
    return allowed.includes(value as T) ? (value as T) : fallback;
  } catch {
    return fallback;
  }
}

function store(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Preferences still apply for this visit.
  }
}

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function summaryOf(chat: Chat): ChatSummary {
  const { id, agent, title, created, updated, running } = chat;
  return { id, agent, title, created, updated, running };
}

type DialogState =
  | { kind: 'rename'; chat: ChatSummary }
  | { kind: 'delete'; chat: ChatSummary }
  | { kind: 'agent'; agent: AgentInfo }
  | { kind: 'memory' }
  | null;

type Toast = { text: string; severity: 'success' | 'error' | 'info' } | null;

export default function App() {
  const prefersDark = useMediaQuery('(prefers-color-scheme: dark)');
  const [modePref, setModePref] = useState<ModePreference>(() => stored('hub-theme', ['light', 'dark', 'system'] as const, 'system'));
  const mode: Mode = modePref === 'system' ? (prefersDark ? 'dark' : 'light') : modePref;
  const theme = useMemo(() => makeTheme(mode), [mode]);
  const desktop = useMediaQuery(theme.breakpoints.up('md'));

  const [route, setRoute] = useState<Route>(parseRoute);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [chats, setChats] = useState<ChatSummary[]>([]);
  const [active, setActive] = useState<Chat | null>(null);
  const [live, setLive] = useState<Record<string, LiveTurn>>({});
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [newAgent, setNewAgent] = useState<AgentKey>(() => stored('hub-agent', ['pair', 'doctor', 'librarian'] as const, 'pair'));
  const [sidebarOpen, setSidebarOpen] = useState(() => stored('hub-sidebar', ['open', 'closed'] as const, 'open') === 'open');
  const [mobileOpen, setMobileOpen] = useState(false);
  const [dialog, setDialog] = useState<DialogState>(null);
  const [toast, setToast] = useState<Toast>(null);

  const chatId = route.kind === 'chat' ? route.id : null;
  const chatIdRef = useRef(chatId);
  chatIdRef.current = chatId;
  const stopped = useRef(new Set<string>());
  const searchRef = useRef<HTMLInputElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const fail = useCallback((text: string) => setToast({ text, severity: 'error' }), []);
  const refreshChats = useCallback(() => api.chats().then(setChats, (error) => fail(message(error))), [fail]);
  const refreshAgents = useCallback(() => api.agents().then(setAgents, (error) => fail(`Could not reach the hub: ${message(error)}`)), [fail]);

  const navigate = useCallback((next: Route, replace = false) => {
    const path = pathOf(next);
    if (path !== window.location.pathname) window.history[replace ? 'replaceState' : 'pushState'](null, '', path);
    setRoute(next);
    setMobileOpen(false);
  }, []);

  /** Show a chat the server sent, unless the user has moved on or a newer copy is already shown. */
  const applyChat = useCallback((chat: Chat) => {
    setActive((current) => {
      if (chatIdRef.current !== chat.id) return current;
      if (current && current.id === chat.id && current.updated > chat.updated) return current;
      return chat;
    });
    setChats((all) => all.map((summary) => (summary.id === chat.id ? summaryOf(chat) : summary)));
  }, []);

  useEffect(() => {
    refreshAgents();
    refreshChats();
    const onPop = () => setRoute(parseRoute());
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, [refreshAgents, refreshChats]);

  // Load the chat the route names.
  useEffect(() => {
    if (!chatId) {
      setActive(null);
      return;
    }
    setActive((current) => (current?.id === chatId ? current : null));
    api.chat(chatId).then(applyChat, (error) => {
      if (chatIdRef.current !== chatId) return;
      fail(message(error));
      navigate({ kind: 'new' }, true);
    });
  }, [chatId, applyChat, fail, navigate]);

  // A turn this tab is not streaming (another tab, or before a reload): look again until it is done.
  const turn = chatId ? live[chatId] : undefined;
  useEffect(() => {
    if (!active?.running || turn) return;
    const timer = setTimeout(() => api.chat(active.id).then(applyChat, () => undefined), 2000);
    return () => clearTimeout(timer);
  }, [active, turn, applyChat]);

  // Titles change on the server (a first message, a rename): keep the open chat's in step.
  useEffect(() => {
    setActive((current) => {
      const summary = chats.find((chat) => chat.id === current?.id);
      return current && summary && summary.title !== current.title ? { ...current, title: summary.title } : current;
    });
  }, [chats]);

  useEffect(() => {
    const agentName = agents.find((a) => a.key === active?.agent)?.name;
    document.title =
      route.kind === 'team' ? 'Codebase Team - Agent Hub' : active?.title ? `${active.title} - ${agentName ?? 'Agent Hub'}` : 'Agent Hub';
  }, [route.kind, active?.title, active?.agent, agents]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const mod = event.ctrlKey || event.metaKey;
      if (mod && !event.shiftKey && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        if (desktop) setSidebarOpen(true);
        else setMobileOpen(true);
        setTimeout(() => searchRef.current?.focus(), 50);
      } else if (mod && event.shiftKey && event.key.toLowerCase() === 'o') {
        event.preventDefault();
        navigate({ kind: 'new' });
        setTimeout(() => inputRef.current?.focus(), 50);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [desktop, navigate]);

  const updateLive = useCallback((id: string, change: (turn: LiveTurn) => LiveTurn | undefined) => {
    setLive((all) => {
      const current = all[id];
      if (!current) return all;
      const next = { ...all };
      const changed = change(current);
      if (changed) next[id] = changed;
      else delete next[id];
      return next;
    });
  }, []);

  const restoreDraft = (id: string, text: string) => setDrafts((all) => (all[id]?.trim() ? all : { ...all, [id]: text }));

  function onTurnEvent(id: string, event: TurnEvent, text: string) {
    switch (event.type) {
      case 'token':
        updateLive(id, (t) => {
          const last = t.parts.at(-1);
          const parts = last?.kind === 'text' ? [...t.parts.slice(0, -1), { kind: 'text' as const, text: last.text + event.text }] : [...t.parts, { kind: 'text' as const, text: event.text }];
          return { ...t, parts };
        });
        break;
      case 'tool_call': {
        const { type: _, ...call } = event;
        updateLive(id, (t) => ({ ...t, parts: [...t.parts, { kind: 'tool', tool: { ...call, status: 'running' } }] }));
        break;
      }
      case 'tool_result':
        updateLive(id, (t) => ({
          ...t,
          parts: t.parts.map((part) =>
            part.kind === 'tool' && part.tool.id === event.id
              ? { kind: 'tool', tool: { ...part.tool, status: event.is_error ? 'error' : 'ok', chars: event.chars } }
              : part,
          ),
        }));
        break;
      case 'stopping':
        updateLive(id, (t) => ({ ...t, status: 'stopping' }));
        break;
      case 'stopped':
        stopped.current.add(id);
        break;
      case 'error':
        updateLive(id, (t) => ({ ...t, status: 'error', error: event.message }));
        break;
      case 'done': {
        const wasStopped = stopped.current.delete(id);
        if (wasStopped && event.session?.messages.length === 0) {
          // A new chat stopped before its first answer: nothing to keep, so go back to where it started.
          updateLive(id, () => undefined);
          setDrafts((all) => (all[NEW_DRAFT]?.trim() ? all : { ...all, [NEW_DRAFT]: text }));
          if (chatIdRef.current === id) navigate({ kind: 'new' }, true);
          api.remove(id).finally(refreshChats);
          break;
        }
        if (event.session) applyChat(event.session);
        updateLive(id, (t) => (t.status === 'error' ? t : undefined));
        if (wasStopped) restoreDraft(id, text); // rolled back: give the words back
        break;
      }
    }
  }

  async function send(text: string) {
    if (!text) return;
    let id = chatId;
    if (!id) {
      try {
        const chat = await api.create(newAgent);
        id = chat.id;
        setDrafts((all) => ({ ...all, [NEW_DRAFT]: '' }));
        setActive(chat);
        setChats((all) => [summaryOf(chat), ...all]);
        chatIdRef.current = id;
        navigate({ kind: 'chat', id });
      } catch (error) {
        fail(message(error));
        return;
      }
    } else {
      setDrafts((all) => ({ ...all, [id!]: '' }));
    }
    const sessionId = id;
    setLive((all) => ({ ...all, [sessionId]: { text, parts: [], status: 'running' } }));
    setTimeout(refreshChats, 400); // the server titles a new chat as its turn starts
    try {
      await streamTurn(sessionId, text, (event) => onTurnEvent(sessionId, event, text));
    } catch (error) {
      updateLive(sessionId, (t) => ({ ...t, status: 'error', error: message(error) }));
      api.chat(sessionId).then(applyChat, () => undefined);
    } finally {
      refreshChats();
    }
  }

  function stop(id: string) {
    updateLive(id, (t) => ({ ...t, status: 'stopping' }));
    api.stop(id).catch((error) => fail(message(error)));
  }

  function retry(id: string) {
    const failed = live[id];
    updateLive(id, () => undefined);
    if (failed) send(failed.text);
  }

  function edit(id: string) {
    const failed = live[id];
    updateLive(id, () => undefined);
    if (failed) restoreDraft(id, failed.text);
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  async function changeModel(agent: AgentKey, model: string) {
    try {
      await api.setModel(agent, model);
      setAgents((all) => all.map((a) => (a.key === agent ? { ...a, model } : a)));
      setToast({ text: `${agents.find((a) => a.key === agent)?.name} now uses ${model}`, severity: 'success' });
    } catch (error) {
      fail(message(error));
    }
  }

  async function rename(chat: ChatSummary, title: string) {
    setDialog(null);
    try {
      await api.rename(chat.id, title);
      await refreshChats();
    } catch (error) {
      fail(message(error));
    }
  }

  async function remove(chat: ChatSummary) {
    setDialog(null);
    try {
      await api.remove(chat.id);
      if (chatId === chat.id) navigate({ kind: 'new' });
      await refreshChats();
      setToast({ text: 'Chat deleted', severity: 'info' });
    } catch (error) {
      fail(message(error));
    }
  }

  async function exportChat(chat: ChatSummary) {
    try {
      downloadJson(`${slug(chat.title)}.json`, await api.exportChat(chat.id));
    } catch (error) {
      fail(message(error));
    }
  }

  async function importChat(file: File) {
    try {
      const chat = await api.importChat(file.name, JSON.parse(await file.text()));
      await refreshChats();
      navigate({ kind: 'chat', id: chat.id });
      setToast({ text: `Imported ${file.name}`, severity: 'success' });
    } catch (error) {
      fail(`Could not import ${file.name}: ${message(error)}`);
    }
  }

  const chooseAgent = (agent: AgentKey) => {
    setNewAgent(agent);
    store('hub-agent', agent);
  };

  const setSidebar = (open: boolean) => {
    setSidebarOpen(open);
    store('hub-sidebar', open ? 'open' : 'closed');
  };

  const isRunning = (chat: ChatSummary) => (live[chat.id] ? live[chat.id].status !== 'error' : chat.running);
  const chatAgent = agents.find((a) => a.key === (active?.agent ?? newAgent));
  const pickerAgent = agents.find((a) => a.key === (route.kind === 'chat' ? active?.agent : route.kind === 'new' ? newAgent : 'team'));
  const draftKey = chatId ?? NEW_DRAFT;

  const sidebar = (
    <Sidebar
      agents={agents}
      chats={chats.filter((chat) => chat.title || chat.id === chatId || isRunning(chat))}
      activeChatId={chatId}
      teamActive={route.kind === 'team'}
      isRunning={isRunning}
      onNewChat={(agent) => {
        if (agent) chooseAgent(agent);
        navigate({ kind: 'new' });
        setTimeout(() => inputRef.current?.focus(), 50);
      }}
      onOpenTeam={() => navigate({ kind: 'team', task: null })}
      onSelect={(id) => navigate({ kind: 'chat', id })}
      onRename={(chat) => setDialog({ kind: 'rename', chat })}
      onDelete={(chat) => setDialog({ kind: 'delete', chat })}
      onExport={exportChat}
      onImport={importChat}
      onClose={() => (desktop ? setSidebar(false) : setMobileOpen(false))}
      searchRef={searchRef}
    />
  );
  const showOpener = !desktop || !sidebarOpen;

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', height: '100dvh', bgcolor: 'background.default', overflow: 'hidden' }}>
        {desktop ? (
          <Box sx={{ width: sidebarOpen ? SIDEBAR_WIDTH : 0, flexShrink: 0, overflow: 'hidden', transition: theme.transitions.create('width', { duration: 200 }) }}>
            {sidebar}
          </Box>
        ) : (
          <Drawer open={mobileOpen} onClose={() => setMobileOpen(false)}>
            {sidebar}
          </Drawer>
        )}

        <Box component="main" sx={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
          <Box component="header" sx={{ display: 'flex', alignItems: 'center', gap: 0.75, px: { xs: 1, sm: 1.5 }, minHeight: 56, borderBottom: 1, borderColor: route.kind === 'new' ? 'transparent' : 'border' }}>
            {showOpener && (
              <>
                <Tooltip title="Open sidebar">
                  <IconButton size="small" onClick={() => (desktop ? setSidebar(true) : setMobileOpen(true))} aria-label="Open sidebar">
                    <ViewSidebarOutlinedIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                <Tooltip title="New chat">
                  <IconButton size="small" onClick={() => navigate({ kind: 'new' })} aria-label="New chat">
                    <EditSquareIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </>
            )}
            <Box sx={{ flex: 1, minWidth: 0, display: 'flex', alignItems: 'center', gap: 1.25, pl: showOpener ? 0.5 : 1 }}>
              {route.kind === 'chat' && active && (
                <>
                  <AgentAvatar agent={active.agent} size={24} />
                  <Tooltip title="Rename" placement="bottom-start">
                    <Typography
                      noWrap
                      role="button"
                      tabIndex={0}
                      onClick={() => setDialog({ kind: 'rename', chat: summaryOf(active) })}
                      onKeyDown={(event) => event.key === 'Enter' && setDialog({ kind: 'rename', chat: summaryOf(active) })}
                      sx={{ fontWeight: 600, fontSize: '0.9375rem', cursor: 'pointer', minWidth: 0, borderRadius: 1, px: 0.5, mx: -0.5, '&:hover': { bgcolor: 'background.hover' } }}
                    >
                      {active.title || 'Untitled'}
                    </Typography>
                  </Tooltip>
                </>
              )}
              {route.kind === 'team' && (
                <>
                  <AgentAvatar agent="team" size={24} />
                  <Typography sx={{ fontWeight: 600, fontSize: '0.9375rem' }} noWrap>
                    Codebase Team
                  </Typography>
                </>
              )}
            </Box>
            {route.kind === 'chat' && active && (
              <Tooltip title="Tokens this chat's completed turns used. Input is the whole conversation, resent on every model call.">
                <Typography variant="caption" color="text.secondary" sx={{ display: { xs: 'none', sm: 'block' }, fontVariantNumeric: 'tabular-nums', px: 1, whiteSpace: 'nowrap' }}>
                  {formatTokens(active.usage.input_tokens)} in · {formatTokens(active.usage.output_tokens)} out
                </Typography>
              </Tooltip>
            )}
            {pickerAgent?.available && (
              <Box sx={{ display: { xs: 'none', sm: 'block' } }}>
                <ModelPicker agent={pickerAgent} onChange={(model) => changeModel(pickerAgent.key, model)} />
              </Box>
            )}
            {route.kind === 'chat' && active && chatAgent?.available && (
              <Tooltip title="Working memory">
                <IconButton size="small" onClick={() => setDialog({ kind: 'memory' })} aria-label="Working memory">
                  <DataObjectRoundedIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
            {pickerAgent?.available && pickerAgent.kind === 'chat' && (
              <Tooltip title={`About ${pickerAgent.name}: tools, skills, prompt`}>
                <IconButton size="small" onClick={() => setDialog({ kind: 'agent', agent: pickerAgent })} aria-label="About this agent">
                  <InfoOutlinedIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
            <ThemeMenu
              value={modePref}
              onChange={(next) => {
                setModePref(next);
                store('hub-theme', next);
              }}
            />
          </Box>

          {route.kind === 'new' && (
            <NewChat
              agents={agents}
              agent={newAgent}
              onAgent={chooseAgent}
              onOpenTeam={() => navigate({ kind: 'team', task: null })}
              draft={drafts[NEW_DRAFT] ?? ''}
              onDraft={(value) => setDrafts((all) => ({ ...all, [NEW_DRAFT]: value }))}
              onSend={send}
              inputRef={inputRef}
            />
          )}
          {route.kind === 'chat' && (
            <ChatView
              agent={agents.find((a) => a.key === active?.agent)}
              chat={active}
              live={turn}
              draft={drafts[draftKey] ?? ''}
              onDraft={(value) => setDrafts((all) => ({ ...all, [draftKey]: value }))}
              onSend={send}
              onStop={() => stop(route.id)}
              onRetry={() => retry(route.id)}
              onEdit={() => edit(route.id)}
              inputRef={inputRef}
            />
          )}
          {route.kind === 'team' && (
            <TeamView
              agent={agents.find((a) => a.key === 'team')}
              taskId={route.task}
              onSelect={(task) => navigate({ kind: 'team', task })}
              onError={fail}
            />
          )}
        </Box>
      </Box>

      {dialog?.kind === 'rename' && (
        <RenameDialog initial={dialog.chat.title} onClose={() => setDialog(null)} onSave={(title) => rename(dialog.chat, title)} />
      )}
      {dialog?.kind === 'delete' && (
        <DeleteDialog title={dialog.chat.title} onClose={() => setDialog(null)} onDelete={() => remove(dialog.chat)} />
      )}
      {dialog?.kind === 'agent' && <AgentDialog agent={dialog.agent} onClose={() => setDialog(null)} />}
      {dialog?.kind === 'memory' && active && chatAgent && <MemoryDialog agent={chatAgent} chat={active} onClose={() => setDialog(null)} />}

      <Snackbar open={!!toast} autoHideDuration={toast?.severity === 'error' ? 9000 : 3500} onClose={() => setToast(null)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        {toast ? (
          <Alert severity={toast.severity} variant="filled" onClose={() => setToast(null)} sx={{ maxWidth: 560, boxShadow: 4 }}>
            {toast.text}
          </Alert>
        ) : undefined}
      </Snackbar>
    </ThemeProvider>
  );
}
