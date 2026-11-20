import { Suspense } from "react";
import { AgentHub } from "@/features/agent/agent-hub";

export default function Page() {
  return (
    <Suspense fallback={<p className="text-sm text-[var(--muted)]">Loading…</p>}>
      <AgentHub section="memory" />
    </Suspense>
  );
}
