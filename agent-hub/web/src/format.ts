import type { ChatSummary, LivePart, Message, ToolView } from './types';

export type Part = { kind: 'text'; text: string } | { kind: 'tools'; tools: ToolView[] };

export type Block =
  | { kind: 'user'; text: string }
  | { kind: 'notice'; text: string }
  | { kind: 'assistant'; parts: Part[] };

const HARNESS_PREFIX = '[harness] ';

function pushTools(parts: Part[], tools: ToolView[]): void {
  if (!tools.length) return;
  const last = parts.at(-1);
  if (last?.kind === 'tools') last.tools.push(...tools);
  else parts.push({ kind: 'tools', tools: [...tools] });
}

/** A chat's messages as the thread shows them: each user turn, then one assistant block
 * holding its text and its tool calls, paired with their results. */
export function toBlocks(messages: Message[]): Block[] {
  const results = new Map<string, Extract<Message, { role: 'tool' }>>();
  for (const message of messages) if (message.role === 'tool') results.set(message.tool_call_id, message);

  const blocks: Block[] = [];
  for (const message of messages) {
    if (message.role === 'tool') continue;
    if (message.role === 'user') {
      blocks.push(
        message.content.startsWith(HARNESS_PREFIX)
          ? { kind: 'notice', text: message.content.slice(HARNESS_PREFIX.length) }
          : { kind: 'user', text: message.content },
      );
      continue;
    }
    let block = blocks.at(-1);
    if (block?.kind !== 'assistant') {
      block = { kind: 'assistant', parts: [] };
      blocks.push(block);
    }
    if (message.content.trim()) block.parts.push({ kind: 'text', text: message.content });
    pushTools(
      block.parts,
      (message.tool_calls ?? []).map((call) => {
        const result = results.get(call.id);
        return { ...call, status: result?.is_error ? 'error' : 'ok', chars: result?.content.length, result: result?.content };
      }),
    );
  }
  return blocks;
}

/** A live turn's parts, with consecutive tool calls grouped the way a finished turn shows them. */
export function liveParts(parts: LivePart[]): Part[] {
  const grouped: Part[] = [];
  for (const part of parts) {
    if (part.kind === 'text') grouped.push({ kind: 'text', text: part.text });
    else pushTools(grouped, [part.tool]);
  }
  return grouped;
}

/** `mcp__domain-lang__lookup_term` reads as `lookup_term` from `domain-lang`. */
export function toolLabel(name: string): { tool: string; source: string | null } {
  const [prefix, server, ...rest] = name.split('__');
  return prefix === 'mcp' && rest.length ? { tool: rest.join('__'), source: server } : { tool: name, source: null };
}

/** A skill being loaded reads as that, not as a file read. */
export function skillOf(tool: ToolView): string | null {
  if (tool.name === 'activate_skill') return String(tool.arguments.name ?? '');
  const path = String(tool.arguments.file_path ?? '');
  return tool.name === 'read_file' && path.startsWith('/skills/') && path.endsWith('/SKILL.md')
    ? path.slice('/skills/'.length, -'/SKILL.md'.length)
    : null;
}

export function argumentSummary(args: Record<string, unknown>): string {
  const text = Object.values(args)
    .map((value) => (Array.isArray(value) ? value.join(' ') : value))
    .filter((value) => typeof value === 'string' || typeof value === 'number')
    .join(', ');
  return text.length > 90 ? `${text.slice(0, 90)}...` : text;
}

export function formatTokens(count: number): string {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  return count >= 1000 ? `${(count / 1000).toFixed(1)}k` : String(count);
}

export function relativeTime(iso: string, now = Date.now()): string {
  const seconds = Math.round((now - new Date(iso).getTime()) / 1000);
  if (seconds < 45) return 'just now';
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function groupByDate(chats: ChatSummary[], now = new Date()): [string, ChatSummary[]][] {
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const day = 86_400_000;
  const groups: [string, number][] = [
    ['Today', startOfToday],
    ['Yesterday', startOfToday - day],
    ['Previous 7 days', startOfToday - 7 * day],
    ['Previous 30 days', startOfToday - 30 * day],
    ['Older', -Infinity],
  ];
  const grouped = new Map<string, ChatSummary[]>();
  for (const chat of chats) {
    const updated = new Date(chat.updated).getTime();
    const [label] = groups.find(([, since]) => updated >= since)!;
    grouped.set(label, [...(grouped.get(label) ?? []), chat]);
  }
  return groups.flatMap(([label]) => (grouped.has(label) ? [[label, grouped.get(label)!]] : []));
}

export function downloadJson(filename: string, data: unknown): void {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
  const link = Object.assign(document.createElement('a'), { href: url, download: filename });
  link.click();
  URL.revokeObjectURL(url);
}

export function slug(title: string): string {
  return title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 50) || 'chat';
}

export function shortTask(taskId: string): string {
  const match = taskId.match(/^task-(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})-([0-9a-f]{4})$/);
  if (!match) return taskId;
  const [, y, mo, d, h, mi] = match;
  return new Date(Date.UTC(+y, +mo - 1, +d, +h, +mi)).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
