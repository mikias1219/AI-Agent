import type { Approval, ApprovalRisk, RunEvent } from "../../lib/api/types";

const TITLES: Record<string, string> = {
  google_gmail_send: "Send email",
  google_calendar_create: "Create calendar event",
  google_calendar_update: "Update calendar event",
  telegram_send_message: "Send Telegram message",
  task_create: "Create task",
  task_update_status: "Update task",
  task_delete: "Delete task",
};

export function approvalTitle(toolName: string): string {
  if (TITLES[toolName]) return TITLES[toolName];
  const spaced = toolName.replace(/[_.-]+/g, " ").trim();
  return spaced ? spaced.charAt(0).toUpperCase() + spaced.slice(1) : "Action";
}

export type ApprovalField = { key: string; label: string; value: string; long?: boolean };

const FIELD_LABELS: Record<string, string> = {
  to: "To",
  subject: "Subject",
  body: "Body",
  title: "Title",
  starts_at: "Starts",
  ends_at: "Ends",
  location: "Where",
  chat_id: "Chat",
  text: "Message",
};

const LONG_KEYS = new Set(["body", "text", "notes", "description"]);

/** The exact payload as label/value rows (recipients, subject, body; title and time). */
export function approvalFields(args: Record<string, unknown>): ApprovalField[] {
  return Object.entries(args)
    .filter(([, value]) => value !== undefined && value !== null && String(value).trim() !== "")
    .map(([key, value]) => ({
      key,
      label: FIELD_LABELS[key] ?? key.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase()),
      value: typeof value === "string" ? value : JSON.stringify(value),
      long: LONG_KEYS.has(key),
    }));
}

const RISK_LABELS: Record<ApprovalRisk, string> = {
  low: "Low risk",
  medium: "Medium risk",
  high: "High risk",
};

export function riskLabel(risk: ApprovalRisk): string {
  return RISK_LABELS[risk] ?? "Medium risk";
}

export function riskTone(risk: ApprovalRisk): "neutral" | "warning" | "accent" {
  return risk === "high" ? "warning" : risk === "medium" ? "accent" : "neutral";
}

/** Plain countdown to the expiry; `null` when the approval never expires. */
export function expiryLabel(expiresAt: string | null, now: number = Date.now()): string | null {
  if (!expiresAt) return null;
  const end = new Date(expiresAt).getTime();
  if (Number.isNaN(end)) return null;
  const minutes = Math.floor((end - now) / 60_000);
  if (minutes < 0) return "Expired";
  if (minutes < 1) return "Expires in under a minute";
  const hours = Math.floor(minutes / 60);
  if (hours === 0) return `Expires in ${minutes} min`;
  return `Expires in ${hours} h ${minutes % 60} min`;
}

export function isExpired(approval: Pick<Approval, "expires_at">, now: number = Date.now()) {
  if (!approval.expires_at) return false;
  const end = new Date(approval.expires_at).getTime();
  return !Number.isNaN(end) && end <= now;
}

/** Build the card model from an `approval.required` run event. */
export function approvalFromEvent(event: RunEvent, sessionId = ""): Approval | null {
  if (event.type !== "approval.required") return null;
  const d = event.data;
  const id = typeof d.approval_id === "string" ? d.approval_id : "";
  if (!id) return null;
  const tool = typeof d.tool === "string" ? d.tool : "";
  const risk = d.risk === "low" || d.risk === "high" ? d.risk : "medium";
  return {
    id,
    run_id: event.run_id,
    tool_name: tool,
    summary: typeof d.summary === "string" ? d.summary : "",
    arguments:
      d.arguments && typeof d.arguments === "object"
        ? (d.arguments as Record<string, unknown>)
        : {},
    arguments_hash: typeof d.arguments_hash === "string" ? d.arguments_hash : "",
    risk,
    untrusted_content: d.untrusted_content === true,
    status: "pending",
    user_id: "",
    session_id: sessionId,
    origin: "dashboard",
    created_at: new Date().toISOString(),
    expires_at: typeof d.expires_at === "string" ? d.expires_at : null,
    decided_at: null,
    edited_from: null,
    result: "",
    actionable: true,
  };
}
