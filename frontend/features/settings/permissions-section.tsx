"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusChip } from "@/components/ui/status-chip";
import { apiErrorMessage } from "@/lib/api/client";
import {
  getAgentPermissions,
  patchAgentControl,
  type AgentPermissionTool,
  type ToolPermissionMode,
} from "@/lib/api/agent-control";

const RULES = [
  "Sending email or messages, changing calendar events and deleting anything always wait for your approval.",
  "Reading, drafting and updating your own tasks and reminders run without asking and appear in Activity.",
  "Pause stops everything except reading until you resume.",
];

const MODES: { id: ToolPermissionMode; label: string }[] = [
  { id: "allow", label: "Allow" },
  { id: "ask", label: "Ask" },
  { id: "block", label: "Block" },
];

const ACCESS_LABEL: Record<string, string> = {
  read: "Read",
  prepare: "Prepare",
  execute: "Commit",
  destructive: "Commit",
};

export function PermissionsSection() {
  const [tools, setTools] = useState<AgentPermissionTool[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setTools((await getAgentPermissions()).tools);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function setToolMode(name: string, mode: ToolPermissionMode) {
    setBusy(true);
    setError(null);
    try {
      await patchAgentControl({ tool_permissions: { [name]: mode } });
      setTools((await getAgentPermissions()).tools);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card id="settings-permissions-heading" title="What always holds">
        <ul className="list-disc space-y-2 pl-5 text-sm text-[var(--ink)]">
          {RULES.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </Card>

      <Card
        id="settings-advanced-permissions"
        title="Per-tool access"
        description="Allow, Ask or Block each tool. Commit tools cannot be set to Allow."
      >
        <details className="group">
          <summary className="inline-flex min-h-11 cursor-pointer items-center rounded-[var(--radius)] text-sm font-medium text-[var(--accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]">
            Show the table
          </summary>
          <div className="mt-2">
            {loading ? (
              <div aria-busy="true" className="flex flex-col gap-2">
                <Skeleton heightClass="h-10" />
                <Skeleton heightClass="h-10" />
              </div>
            ) : error && tools.length === 0 ? (
              <div
                className="flex flex-wrap items-center gap-2 text-sm text-[var(--danger)]"
                role="alert"
              >
                {error}
                <Button size="sm" variant="secondary" onClick={() => void load()}>
                  Try again
                </Button>
              </div>
            ) : tools.length === 0 ? (
              <EmptyState
                title="No tools listed"
                description="Tools appear here once the agent has loaded its skills."
              />
            ) : (
              <>
                {error ? (
                  <p className="mb-2 text-sm text-[var(--danger)]" role="alert">
                    {error}
                  </p>
                ) : null}
                <ul className="flex flex-col">
                  {tools.map((tool) => (
                    <li
                      key={tool.name}
                      className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] py-2 last:border-0"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-[var(--ink)]">
                          {tool.name}
                        </p>
                        <StatusChip className="mt-1">
                          {ACCESS_LABEL[tool.access_kind] ?? tool.access_kind}
                        </StatusChip>
                      </div>
                      <div
                        className="flex gap-1"
                        role="group"
                        aria-label={`Access for ${tool.name}`}
                      >
                        {MODES.map((mode) => (
                          <Button
                            key={mode.id}
                            type="button"
                            size="sm"
                            className="min-h-11 min-w-11"
                            variant={tool.mode === mode.id ? "primary" : "secondary"}
                            aria-pressed={tool.mode === mode.id}
                            disabled={busy || (mode.id === "allow" && tool.ceiling)}
                            onClick={() => void setToolMode(tool.name, mode.id)}
                          >
                            {mode.label}
                          </Button>
                        ))}
                      </div>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </details>
      </Card>
    </div>
  );
}
