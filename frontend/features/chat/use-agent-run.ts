"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import { cancelRun, followRun, startRun } from "@/lib/api/runs";
import { applyUndo } from "@/lib/api/undo";
import { applyRunEvent, emptyRunView, isStreamOver, type RunView } from "./run-trail";

export type AgentRunState = {
  view: RunView;
  busy: boolean;
  error: string | null;
  runId: string | null;
  sessionId: string | null;
  question: string | null;
};

const idle: AgentRunState = {
  view: emptyRunView,
  busy: false,
  error: null,
  runId: null,
  sessionId: null,
  question: null,
};

/**
 * One place to start a run and fold its event stream. Used by Chat (via helpers) and Quick ask
 * so both surfaces show the same cards and approval pause.
 */
export function useAgentRun() {
  const [state, setState] = useState<AgentRunState>(idle);
  const abortRef = useRef<AbortController | null>(null);
  const viewRef = useRef<RunView>(emptyRunView);
  const toastedUndo = useRef<Set<string>>(new Set());
  const { toast } = useToast();

  useEffect(() => () => abortRef.current?.abort(), []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    viewRef.current = emptyRunView;
    setState(idle);
  }, []);

  const start = useCallback(async (text: string, sessionId?: string, context?: string) => {
    const question = text.trim();
    if (!question) return null;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    viewRef.current = emptyRunView;
    setState({
      view: emptyRunView,
      busy: true,
      error: null,
      runId: null,
      sessionId: sessionId ?? null,
      question,
    });
    try {
      const run = await startRun({ text: question, sessionId, context });
      setState((prev) => ({ ...prev, runId: run.id, sessionId: run.session_id }));
      let view = emptyRunView;
      await followRun(run.id, {
        signal: controller.signal,
        onEvent: (event) => {
          view = applyRunEvent(view, event);
          viewRef.current = view;
          for (const step of view.steps) {
            if (!step.undoId || toastedUndo.current.has(step.undoId)) continue;
            toastedUndo.current.add(step.undoId);
            const undoId = step.undoId;
            toast(step.resultSummary || step.detail || "Done", {
              tone: "success",
              action: {
                label: "Undo",
                onClick: async () => {
                  try {
                    const result = await applyUndo(undoId);
                    toast(result.summary, "success");
                  } catch (err) {
                    toast(apiErrorMessage(err), "danger");
                  }
                },
              },
            });
          }
          setState((prev) => ({ ...prev, view, runId: run.id, sessionId: run.session_id }));
        },
      });
      if (controller.signal.aborted) return view;
      if (!isStreamOver(view)) {
        throw new Error("The connection ended before the agent finished.");
      }
      setState((prev) => ({
        ...prev,
        busy: false,
        error: view.status === "failed" ? (view.error ?? "The agent could not finish.") : null,
        view,
      }));
      return view;
    } catch (err) {
      if (controller.signal.aborted) return viewRef.current;
      const message = apiErrorMessage(err);
      setState((prev) => ({ ...prev, busy: false, error: message }));
      return null;
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
    }
  }, []);

  const stop = useCallback(async () => {
    const id = state.runId;
    if (!id) {
      abortRef.current?.abort();
      return;
    }
    try {
      await cancelRun(id);
    } catch (err) {
      setState((prev) => ({ ...prev, error: apiErrorMessage(err) }));
    }
  }, [state.runId]);

  return { ...state, start, stop, reset };
}
