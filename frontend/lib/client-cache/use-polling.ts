"use client";

import { useCallback, useEffect, useRef } from "react";

/**
 * Shared poll helper: one interval, pause while the tab is hidden, refresh on focus.
 */
export function usePolling(callback: () => void, intervalMs: number, enabled = true): void {
  const saved = useRef(callback);
  useEffect(() => {
    saved.current = callback;
  }, [callback]);

  const tick = useCallback(() => {
    if (typeof document !== "undefined" && document.visibilityState === "hidden") return;
    saved.current();
  }, []);

  useEffect(() => {
    if (!enabled) return;
    tick();
    const id = window.setInterval(tick, intervalMs);
    function onVisible() {
      if (document.visibilityState === "visible") tick();
    }
    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("focus", onVisible);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("focus", onVisible);
    };
  }, [enabled, intervalMs, tick]);
}
