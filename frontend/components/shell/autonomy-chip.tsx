"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { StatusChip } from "@/components/ui/status-chip";
import { AUTONOMY_LABELS, getAgentControl, type AutonomyPresetId } from "@/lib/api/agent-control";

export type AutonomyChipProps = {
  preset?: string;
  className?: string;
};

/** Header chip showing the current autonomy preset; links to Settings → Permissions. */
export function AutonomyChip({ preset, className = "" }: AutonomyChipProps) {
  const [label, setLabel] = useState(preset ?? "Balanced");

  useEffect(() => {
    if (preset) {
      setLabel(preset);
      return;
    }
    let cancelled = false;
    getAgentControl()
      .then((state) => {
        if (cancelled) return;
        setLabel(AUTONOMY_LABELS[state.autonomy_preset as AutonomyPresetId] ?? "Balanced");
      })
      .catch(() => {
        /* keep default label when control is unavailable */
      });
    return () => {
      cancelled = true;
    };
  }, [preset]);

  return (
    <Link
      href="/settings?section=permissions"
      title={`Autonomy: ${label}. Open permissions settings.`}
      aria-label={`Autonomy preset: ${label}`}
      className={`rounded-full focus-visible:outline-2 focus-visible:outline-[var(--accent)] ${className}`.trim()}
    >
      <StatusChip tone="accent" className="gap-1.5">
        <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
        {label}
      </StatusChip>
    </Link>
  );
}
