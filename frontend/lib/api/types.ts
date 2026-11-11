export type User = {
  name: string;
  email: string;
};

export type AuthStatus = {
  authenticated: boolean;
  registered: boolean;
  user: User | null;
  email_required: boolean;
};

export type LoginResponse = {
  authenticated: true;
  user: User;
};

export type RegisterResponse = {
  registered: true;
};

export type ModelSetupPayload = {
  status: string;
  model: string;
  updated_at: string;
  restart_required: boolean;
};

export type TelegramStatusPayload = {
  configured: boolean;
  allowed_chat_ids: number[];
  command: string;
  managed: boolean;
  runtime: string;
  last_seen: string | null;
  username: string | null;
  error_type?: string | null;
};

export type StatusPayload = {
  provider: string;
  model_setup: ModelSetupPayload | null;
  model: string;
  active_runtime: string;
  runtime_reason: string | null;
  hermes_installed: boolean;
  ollama_reachable: boolean;
  telegram: TelegramStatusPayload;
};

export type ChatToolCall = {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
};

export type ChatMessage = {
  role: string;
  content: string;
  name: string | null;
  tool_call_id: string | null;
  tool_calls: ChatToolCall[];
};

export type ChatTurnResponse = {
  session_id: string;
  reply: string;
};

export type ChatStreamEvent =
  | { type: "delta"; text: string }
  | { type: "done"; session_id: string; reply: string }
  | { type: "error"; detail: string };

export type RunStatus = "running" | "awaiting_approval" | "completed" | "failed" | "cancelled";

export type RunSummary = {
  id: string;
  session_id: string;
  origin: string;
  status: RunStatus;
  prompt_version: string;
  model: string;
  input: string;
  reply: string;
  error: string;
  stop_reason: string | null;
  created_at: string | null;
  finished_at: string | null;
};

export type RunEventType =
  | "run.started"
  | "token"
  | "tool.started"
  | "tool.finished"
  | "approval.required"
  | "approval.resolved"
  | "run.completed"
  | "run.failed";

export type RunEvent = {
  seq: number;
  run_id: string;
  type: RunEventType;
  data: Record<string, unknown>;
};

export type ConversationSummary = {
  id: string;
  user_id: string;
  created_at: string;
};

export type TaskStatus = "planned" | "in_progress" | "blocked" | "done" | "cancelled";

export type TaskPriority = "p1" | "p2" | "p3" | "none";

export type Task = {
  id: string;
  title: string;
  description: string;
  status: TaskStatus;
  owner_user_id: string;
  priority: TaskPriority;
  due_at: string | null;
  project: string;
  tags: string[];
  source: string;
  created_at: string | null;
  updated_at: string | null;
  completed_at: string | null;
};

export type ApprovalDecision = "approve" | "reject";

export type ApprovalStatus =
  "pending" | "approved" | "denied" | "expired" | "executed" | "failed" | "superseded";

export type ApprovalRisk = "low" | "medium" | "high";

export type Approval = {
  id: string;
  run_id: string | null;
  tool_name: string;
  /** One plain-language line about what will happen. */
  summary: string;
  arguments: Record<string, unknown>;
  arguments_hash: string;
  risk: ApprovalRisk;
  /** True when email, documents or web content was read in this run (BR-04). */
  untrusted_content: boolean;
  status: ApprovalStatus;
  user_id: string;
  session_id: string;
  origin: string;
  created_at: string;
  expires_at: string | null;
  decided_at: string | null;
  edited_from: string | null;
  result: string;
  actionable: boolean;
};

export type ApprovalDecisionResponse = {
  id: string;
  decision: "approved" | "denied";
  status: ApprovalStatus;
  /** True only for the call that actually ran the tool; repeats return false. */
  executed: boolean;
  ok: boolean | null;
  result: string;
  run_id: string | null;
  approval: Approval;
};

export type ActivityEvent = {
  id: number;
  occurred_at: string;
  actor: string;
  event: string;
  details: Record<string, unknown>;
};
