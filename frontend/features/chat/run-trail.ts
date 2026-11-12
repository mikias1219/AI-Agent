import type {
  Approval,
  MemoryKind,
  MemoryProposal,
  RunEvent,
  UsedMemory,
} from "../../lib/api/types";
import { approvalFromEvent } from "../approvals/approval-format";

export type TrailStepStatus = "running" | "ok" | "failed";

export type TrailStep = {
  id: string;
  name: string;
  status: TrailStepStatus;
  durationMs?: number;
  detail?: string;
  /** Set while the gate waits for a human decision on this step. */
  approval?: "waiting" | "approved" | "denied" | "deferred";
};

export type RunView = {
  steps: TrailStep[];
  content: string;
  status: "running" | "awaiting_approval" | "completed" | "failed" | "cancelled";
  /** Highest event number folded in; reconnect with `after=lastSeq` to continue. */
  lastSeq: number;
  /** The pending approval while the run is paused for the owner. */
  approval?: Approval;
  sessionId?: string;
  error?: string;
  stopReason?: string | null;
  memoryProposal?: MemoryProposal;
  usedMemories?: UsedMemory[];
};

export const emptyRunView: RunView = { steps: [], content: "", status: "running", lastSeq: 0 };

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

/** Fold one run event into the view model the chat renders (pure; easy to test). */
export function applyRunEvent(view: RunView, event: RunEvent): RunView {
  const next = foldEvent(view, event);
  return event.seq > next.lastSeq ? { ...next, lastSeq: event.seq } : next;
}

function foldEvent(view: RunView, event: RunEvent): RunView {
  const { data } = event;
  switch (event.type) {
    case "run.started":
      return { ...view, sessionId: text(data.session_id) || view.sessionId };
    case "token":
      return { ...view, content: view.content + text(data.text) };
    case "tool.started":
      return {
        ...view,
        steps: [
          ...view.steps,
          {
            id: text(data.call_id) || `step-${view.steps.length}`,
            name: text(data.name),
            status: "running",
          },
        ],
      };
    case "tool.finished": {
      const id = text(data.call_id);
      return {
        ...view,
        steps: view.steps.map((step) =>
          step.id === id
            ? {
                ...step,
                status: data.ok ? "ok" : "failed",
                durationMs: typeof data.duration_ms === "number" ? data.duration_ms : undefined,
                detail: text(data.output).slice(0, 300) || undefined,
                approval: step.approval === "waiting" ? undefined : step.approval,
              }
            : step,
        ),
      };
    }
    case "approval.required": {
      const waiting = withLatestRunningStep(view, (step) => ({ ...step, approval: "waiting" }));
      // A durable approval ends the stream: the run is paused until the owner decides.
      return data.durable === true
        ? {
            ...waiting,
            status: "awaiting_approval",
            approval: approvalFromEvent(event) ?? undefined,
          }
        : waiting;
    }
    case "approval.resolved": {
      const raw = text(data.decision);
      const decision = (
        raw === "approved" || raw === "denied" ? raw : "deferred"
      ) as TrailStep["approval"];
      const resolved = withLatestRunningStep(view, (step) => ({ ...step, approval: decision }));
      return resolved.status === "awaiting_approval"
        ? { ...resolved, status: "running", approval: undefined }
        : resolved;
    }
    case "memory.proposed": {
      const kind = text(data.kind) as MemoryKind;
      const content = text(data.content);
      if (!content || !kind) return view;
      return {
        ...view,
        memoryProposal: {
          kind,
          content,
          source_run_id: text(data.run_id) || null,
        },
      };
    }
    case "memory.used": {
      const raw = Array.isArray(data.items) ? data.items : [];
      const usedMemories = raw.flatMap((item) => {
        if (!item || typeof item !== "object") return [];
        const row = item as Record<string, unknown>;
        const id = text(row.id);
        const kind = text(row.kind) as MemoryKind;
        const content = text(row.content);
        if (!id || !kind || !content) return [];
        return [{ id, kind, content } satisfies UsedMemory];
      });
      return usedMemories.length ? { ...view, usedMemories } : view;
    }
    case "run.completed":
      return {
        ...view,
        status: "completed",
        content: text(data.reply) || view.content,
        stopReason: typeof data.stop_reason === "string" ? data.stop_reason : null,
      };
    case "run.failed":
      return data.status === "cancelled"
        ? {
            ...view,
            status: "cancelled",
            content: text(data.reply) || view.content,
            stopReason: "cancelled",
          }
        : { ...view, status: "failed", error: text(data.error) || "The agent could not finish." };
    default:
      return view;
  }
}

function withLatestRunningStep(view: RunView, update: (step: TrailStep) => TrailStep): RunView {
  const index = [...view.steps].reverse().findIndex((step) => step.status === "running");
  if (index < 0) return view;
  const target = view.steps.length - 1 - index;
  return { ...view, steps: view.steps.map((step, i) => (i === target ? update(step) : step)) };
}

export function isTerminal(view: RunView): boolean {
  return view.status !== "running" && view.status !== "awaiting_approval";
}

/** The server closes the stream at a terminal event or when the run pauses for approval. */
export function isStreamOver(view: RunView): boolean {
  return view.status !== "running";
}

export function stepLabel(name: string): string {
  const spaced = name.replace(/[_.-]+/g, " ").trim();
  return spaced ? spaced.charAt(0).toUpperCase() + spaced.slice(1) : "Step";
}

export function formatDuration(ms: number | undefined): string {
  if (ms === undefined) return "";
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`;
}

export function trailSummary(steps: TrailStep[], pending: boolean): string {
  const count = steps.length;
  if (pending)
    return count === 0 ? "Working…" : `Working… ${count} ${count === 1 ? "step" : "steps"}`;
  return `Used ${count} ${count === 1 ? "tool" : "tools"}`;
}
