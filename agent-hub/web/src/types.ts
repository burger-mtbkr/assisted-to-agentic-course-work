export type AgentKey = 'pair' | 'doctor' | 'librarian' | 'team';

export type AgentInfo = {
  key: AgentKey;
  kind: 'chat' | 'workflow';
  name: string;
  module: string;
  summary: string;
  available: boolean;
  reason: string | null;
  model?: string;
  models?: string[];
  system_prompt?: string;
  max_rounds?: number;
  skills?: { name: string; description: string }[];
  tools?: { name: string; source: string; description: string }[];
  scenarios?: { name: string; description: string }[];
  tests_command?: string;
};

export type ToolCall = { id: string; name: string; arguments: Record<string, unknown> };

export type Message =
  | { role: 'user'; content: string }
  | { role: 'assistant'; content: string; tool_calls?: ToolCall[] }
  | { role: 'tool'; tool_call_id: string; name: string; content: string; is_error?: boolean };

export type Usage = { input_tokens: number; output_tokens: number };

export type ChatSummary = {
  id: string;
  agent: AgentKey;
  title: string;
  created: string;
  updated: string;
  running: boolean;
};

export type Chat = ChatSummary & { usage: Usage; messages: Message[]; state: unknown[] };

export type TurnEvent =
  | { type: 'token'; text: string }
  | ({ type: 'tool_call' } & ToolCall)
  | { type: 'tool_result'; id: string; name: string; is_error: boolean; chars: number }
  | { type: 'stopping' }
  | { type: 'stopped' }
  | { type: 'error'; message: string }
  | { type: 'done'; session: Chat | null };

export type ToolStatus = 'running' | 'ok' | 'error';
export type ToolView = ToolCall & { status: ToolStatus; chars?: number; result?: string };

export type LivePart = { kind: 'text'; text: string } | { kind: 'tool'; tool: ToolView };

/** A turn in flight, as this browser tab sees it. */
export type LiveTurn = {
  text: string;
  parts: LivePart[];
  status: 'running' | 'stopping' | 'error';
  error?: string;
};

export type RunState = 'running' | 'awaiting_approval' | 'approved' | 'rejected' | 'finished' | 'interrupted';

export type RunSummary = {
  task_id: string;
  created: string;
  scenario: string | null;
  scenario_description: string | null;
  state: RunState;
  step?: { agent: string; request_type: string } | null;
  outcome?: string;
  claim?: string;
};

export type Evidence = { source: string; kind: string; detail: string };

export type Diagnosis = {
  status: string;
  failing_checks: string[];
  failing_tests: string[];
  observed_error: string;
  relevant_files: string[];
  suspected_cause: string;
  evidence: Evidence[];
  uncertainty: string[];
  recommended_next_step: string;
  test_counts: Record<string, number>;
};

export type Brief = {
  relevant_docs: string[];
  relevant_memory_notes: string[];
  relevant_source_files: string[];
  relevant_tests: string[];
  git_evidence: string[];
  facts: string[];
  suggested_constraints: string[];
  gaps: string[];
  confidence: number;
};

export type Approval = {
  approved: boolean;
  approved_by: string;
  allowed_paths: string[];
  allowed_commands: string[];
  rationale: string;
};

export type Patch = {
  mode: string;
  intent: string;
  files_changed: string[];
  diff_summary: string;
  rationale: string;
  risks: string[];
  verification_request: string;
};

export type Verification = {
  status: string;
  checks_run: string[];
  passed: boolean;
  remaining_failures: string[];
  files_inspected: string[];
  recommendation: string;
};

export type TrajectoryEvent = { seq: number; timestamp: string; event: string } & Record<string, unknown>;

export type RunDetail = RunSummary & {
  source: string;
  workspace: string;
  timeline: TrajectoryEvent[];
  artifacts: {
    diagnosis: Diagnosis | null;
    brief: Brief | null;
    approval: Approval | null;
    patch: Patch | null;
    verification: Verification | null;
  };
  changed_files: string[];
  diff: string;
  evals: { group: string; name: string; passed: boolean; detail: string }[];
};
