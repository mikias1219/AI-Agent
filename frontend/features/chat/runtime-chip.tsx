"use client";

import { useEffect, useState } from "react";
import { getStatus } from "@/lib/api/status";

export function RuntimeChip() {
  const [label, setLabel] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getStatus()
      .then((s) => {
        if (!cancelled) setLabel(`${s.provider} · ${s.model} · ${s.active_runtime}`);
      })
      .catch(() => {
        if (!cancelled) setLabel(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!label) return null;
  return (
    <p className="text-xs text-[var(--muted)]" aria-label="Agent runtime">
      {label}
    </p>
  );
}
