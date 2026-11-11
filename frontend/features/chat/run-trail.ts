import type { RunEvent } from "../../lib/api/types";

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
  status: "running" | "completed" | "failed" | "cancelled";
  sessionId?: string;
  error?: string;
  stopReason?: string | null;
};

export const emptyRunView: RunView = { steps: [], content: "", status: "running" };

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

/** Fold one run event into the view model the chat renders (pure; easy to test). */
export function applyRunEvent(view: RunView, event: RunEvent): RunView {
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
    case "approval.required":
      return withLatestRunningStep(view, (step) => ({ ...step, approval: "waiting" }));
    case "approval.resolved": {
      const decision = text(data.decision) as TrailStep["approval"];
      return withLatestRunningStep(view, (step) => ({ ...step, approval: decision }));
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
