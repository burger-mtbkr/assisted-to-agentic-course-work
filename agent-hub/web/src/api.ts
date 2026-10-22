import type { AgentInfo, AgentKey, Chat, ChatSummary, RunDetail, RunSummary, TurnEvent } from './types';

async function failure(response: Response): Promise<Error> {
  const body = await response.json().catch(() => null);
  return new Error(body?.error ?? `${response.status} ${response.statusText}`);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, { ...init, headers: { 'Content-Type': 'application/json', ...init.headers } });
  if (!response.ok) throw await failure(response);
  return (response.status === 204 ? undefined : await response.json()) as T;
}

const send = (method: string, body: unknown = {}): RequestInit => ({ method, body: JSON.stringify(body) });

export const api = {
  agents: () => request<AgentInfo[]>('/api/agents'),
  setModel: (agent: AgentKey, model: string) => request<{ model: string }>(`/api/agents/${agent}/model`, send('PUT', { model })),

  chats: () => request<ChatSummary[]>('/api/sessions'),
  chat: (id: string) => request<Chat>(`/api/sessions/${id}`),
  create: (agent: AgentKey) => request<Chat>('/api/sessions', send('POST', { agent })),
  importChat: (filename: string, data: unknown) => request<Chat>('/api/sessions/import', send('POST', { filename, data })),
  exportChat: (id: string) => request<unknown>(`/api/sessions/${id}/export`),
  rename: (id: string, title: string) => request<{ title: string }>(`/api/sessions/${id}`, send('PATCH', { title })),
  remove: (id: string) => request<void>(`/api/sessions/${id}`, { method: 'DELETE' }),
  stop: (id: string) => request<void>(`/api/sessions/${id}/stop`, send('POST')),

  runs: () => request<RunSummary[]>('/api/team/runs'),
  run: (task: string) => request<RunDetail>(`/api/team/runs/${task}`),
  startRun: (scenario: string | null) => request<RunSummary>('/api/team/runs', send('POST', { scenario })),
  approveRun: (task: string, body: { paths: string[]; rationale: string; allow_tests: boolean; approved: boolean }) =>
    request<RunDetail>(`/api/team/runs/${task}/approve`, send('POST', body)),
  continueRun: (task: string, remember: boolean) =>
    request<RunDetail>(`/api/team/runs/${task}/continue`, send('POST', { remember })),
};

/** Send one message and report the turn's newline-delimited JSON events as they arrive.
 * Throws if the stream ends before the turn's `done`, so a dropped connection never looks
 * like a turn still running. */
export async function streamTurn(id: string, text: string, onEvent: (event: TurnEvent) => void): Promise<void> {
  const response = await fetch(`/api/sessions/${id}/messages`, {
    ...send('POST', { text }),
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok || !response.body) throw await failure(response);
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) throw new Error('The connection to the hub closed before the turn finished.');
    buffer += value;
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (!line.trim()) continue;
      const event = JSON.parse(line) as TurnEvent;
      onEvent(event);
      if (event.type === 'done') return;
    }
  }
}
