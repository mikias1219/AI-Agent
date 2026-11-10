"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { Spinner } from "@/components/ui/spinner";
import { getStatus } from "@/lib/api/status";
import type { StatusPayload } from "@/lib/api/types";
import { Badge } from "@/components/ui/badge";

const panelClass =
  "rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-4 sm:px-5";

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">{label}</dt>
      <dd className="mt-1 text-sm font-medium text-[var(--ink)]">{children}</dd>
    </div>
  );
}

export function RuntimeSection() {
  const [status, setStatus] = useState<StatusPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getStatus()
      .then((payload) => {
        if (cancelled) return;
        setStatus(payload);
        setUnavailable(false);
      })
      .catch(() => {
        if (cancelled) return;
        setStatus(null);
        setUnavailable(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className={panelClass} aria-labelledby="settings-runtime-heading">
      <h2 id="settings-runtime-heading" className="text-sm font-semibold text-[var(--ink)]">
        Agent runtime
      </h2>
      <p className="mt-1 text-sm text-[var(--muted)]">
        Live fields from{" "}
        <code className="rounded bg-[var(--canvas)] px-1 text-xs">GET /api/status</code>. Configure
        models and tokens in the backend environment, not in this dashboard.
      </p>

      {loading ? (
        <div className="mt-4 flex items-center gap-2 text-sm text-[var(--muted)]">
          <Spinner size="sm" />
          Loading status…
        </div>
      ) : unavailable || !status ? (
        <p className="mt-4 text-sm text-[var(--warning)]">
          Could not reach the backend status endpoint. Start the agent on port 8000 and refresh.
        </p>
      ) : (
        <dl className="mt-4 grid gap-4 sm:grid-cols-2">
          <Field label="Provider">{status.provider}</Field>
          <Field label="Model">{status.model}</Field>
          <Field label="Active runtime">{status.active_runtime}</Field>
          <Field label="Runtime reason">{status.runtime_reason || "—"}</Field>
          <Field label="Hermes installed">{status.hermes_installed ? "Yes" : "No"}</Field>
          <Field label="Ollama reachable">{status.ollama_reachable ? "Yes" : "No"}</Field>
          <Field label="Telegram">
            <span className="inline-flex flex-wrap items-center gap-2">
              {status.telegram.configured ? (
                <Badge tone="accent">Configured</Badge>
              ) : (
                <Badge tone="neutral">Not configured</Badge>
              )}
              {status.telegram.managed ? (
                <span className="text-xs font-normal text-[var(--muted)]">
                  Managed · {status.telegram.runtime || "unknown"}
                </span>
              ) : null}
            </span>
          </Field>
          {status.model_setup ? (
            <>
              <Field label="Model setup status">{status.model_setup.status}</Field>
              <Field label="Setup updated">
                <time dateTime={status.model_setup.updated_at}>
                  {status.model_setup.updated_at}
                </time>
              </Field>
            </>
          ) : null}
        </dl>
      )}

      <p className="mt-4 text-sm text-[var(--muted)]">
        Telegram controls live under{" "}
        <Link
          href="/connections/telegram"
          className="font-medium text-[var(--accent)] hover:underline"
        >
          Connections → Telegram
        </Link>
        . Inference uses local Ollama when available; paid cloud model APIs are not wired here.
      </p>
    </section>
  );
}
