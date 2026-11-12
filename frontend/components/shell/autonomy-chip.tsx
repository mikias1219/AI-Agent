import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { StatusChip } from "@/components/ui/status-chip";

export type AutonomyPreset = "Cautious" | "Balanced" | "Proactive";

/** Local default until the agent-control API (Task 2) supplies the saved preset. */
export const DEFAULT_AUTONOMY_PRESET: AutonomyPreset = "Balanced";

export type AutonomyChipProps = {
  preset?: string;
  className?: string;
};

/** Header chip showing the current autonomy preset; links to Settings → Permissions. */
export function AutonomyChip({
  preset = DEFAULT_AUTONOMY_PRESET,
  className = "",
}: AutonomyChipProps) {
  return (
    <Link
      href="/settings?section=permissions"
      title={`Autonomy: ${preset}. Open permissions settings.`}
      aria-label={`Autonomy preset: ${preset}`}
      className={`rounded-full focus-visible:outline-2 focus-visible:outline-[var(--accent)] ${className}`.trim()}
    >
      <StatusChip tone="accent" className="gap-1.5">
        <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
        {preset}
      </StatusChip>
    </Link>
  );
}
