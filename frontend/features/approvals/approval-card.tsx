"use client";

import { useEffect, useState } from "react";
import { TriangleAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { decideApproval, editApproval } from "@/lib/api/approvals";
import { apiErrorMessage } from "@/lib/api/client";
import type { Approval, ApprovalDecision, ApprovalDecisionResponse } from "@/lib/api/types";
import {
  approvalFields,
  approvalTitle,
  expiryLabel,
  isExpired,
  riskLabel,
  riskTone,
} from "./approval-format";

export type ApprovalCardProps = {
  approval: Approval;
  /** Called once the decision is recorded (and, for approve, the action has run). */
  onDecided: (response: ApprovalDecisionResponse) => void;
  /** Called when an edit replaced this approval, so the parent can show the new one. */
  onReplaced?: (replacement: Approval) => void;
};

/** The single approval UI used in Chat and in Tasks → Approvals (APR-03). */
export function ApprovalCard({ approval, onDecided, onReplaced }: ApprovalCardProps) {
  const [now, setNow] = useState(() => Date.now());
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<ApprovalDecision | "edit" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 30_000);
    return () => window.clearInterval(id);
  }, []);

  const fields = approvalFields(approval.arguments);
  const expired = isExpired(approval, now);
  const waiting = approval.actionable && !expired;
  const countdown = expiryLabel(approval.expires_at, now);
  const title = approvalTitle(approval.tool_name);

  function startEdit() {
    const next: Record<string, string> = {};
    for (const field of fields) next[field.key] = field.value;
    setDraft(next);
    setError(null);
    setEditing(true);
  }

  function editedArguments(): Record<string, unknown> {
    const args: Record<string, unknown> = { ...approval.arguments };
    for (const [key, value] of Object.entries(draft)) {
      args[key] = typeof approval.arguments[key] === "string" ? value : tryJson(value);
    }
    return args;
  }

  async function decide(decision: ApprovalDecision) {
    setError(null);
    setBusy(decision);
    try {
      onDecided(await decideApproval(approval.id, decision));
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function approveEdited() {
    setError(null);
    setBusy("edit");
    let replacement: Approval;
    try {
      replacement = await editApproval(approval.id, editedArguments());
    } catch (err) {
      setError(apiErrorMessage(err));
      setBusy(null);
      return;
    }
    // The edit created a new approval with a new hash; it needs its own approval.
    try {
      setEditing(false);
      onDecided(await decideApproval(replacement.id, "approve"));
    } catch (err) {
      onReplaced?.(replacement);
      setError(apiErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section
      aria-label={`Approval: ${title}`}
      className="flex flex-col gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4"
    >
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-[var(--ink)]">{title}</p>
          <p className="mt-0.5 text-sm text-[var(--muted)]">
            {approval.summary || "The agent wants to take this action."}
          </p>
        </div>
        <Badge tone={riskTone(approval.risk)}>{riskLabel(approval.risk)}</Badge>
      </header>

      {approval.untrusted_content ? (
        <p
          role="note"
          className="flex items-start gap-2 rounded-[var(--radius)] border border-[#f9dbaf] bg-[#fef3eb] px-3 py-2 text-sm text-[var(--warning)]"
        >
          <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>
            This request came after reading an email, document or web page. Check the details
            carefully: outside content cannot give the agent orders.
          </span>
        </p>
      ) : null}

      {editing ? (
        <div className="flex flex-col gap-3">
          {fields.map((field) => (
            <div key={field.key} className="flex flex-col gap-1">
              <label
                htmlFor={`${approval.id}-${field.key}`}
                className="text-xs font-medium text-[var(--muted)]"
              >
                {field.label}
              </label>
              {field.long ? (
                <Textarea
                  id={`${approval.id}-${field.key}`}
                  value={draft[field.key] ?? ""}
                  onChange={(event) => setDraft({ ...draft, [field.key]: event.target.value })}
                />
              ) : (
                <Input
                  id={`${approval.id}-${field.key}`}
                  value={draft[field.key] ?? ""}
                  onChange={(event) => setDraft({ ...draft, [field.key]: event.target.value })}
                />
              )}
            </div>
          ))}
          <p className="text-xs text-[var(--muted)]">
            Saving creates a new request. Your earlier approval can no longer be used.
          </p>
        </div>
      ) : (
        <dl className="flex flex-col gap-1.5 text-sm">
          {fields.map((field) => (
            <div key={field.key} className="grid grid-cols-[5.5rem_1fr] gap-2">
              <dt className="text-[var(--muted)]">{field.label}</dt>
              <dd className="break-words whitespace-pre-wrap text-[var(--ink)]">{field.value}</dd>
            </div>
          ))}
        </dl>
      )}

      {error ? (
        <p className="text-sm text-[var(--danger)]" role="alert">
          {error}
        </p>
      ) : null}

      {waiting ? (
        <footer className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs text-[var(--muted)]" role="status">
            {countdown}
          </p>
          <div className="flex flex-wrap justify-end gap-2">
            {editing ? (
              <>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={busy !== null}
                  onClick={() => setEditing(false)}
                >
                  Cancel edit
                </Button>
                <Button
                  size="sm"
                  loading={busy === "edit"}
                  disabled={busy !== null}
                  onClick={approveEdited}
                >
                  Approve edited
                </Button>
              </>
            ) : (
              <>
                <Button variant="secondary" size="sm" disabled={busy !== null} onClick={startEdit}>
                  Edit then approve
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  loading={busy === "reject"}
                  disabled={busy !== null}
                  onClick={() => void decide("reject")}
                >
                  Deny
                </Button>
                <Button
                  size="sm"
                  loading={busy === "approve"}
                  disabled={busy !== null}
                  onClick={() => void decide("approve")}
                >
                  Approve
                </Button>
              </>
            )}
          </div>
        </footer>
      ) : (
        <p className="text-sm text-[var(--muted)]" role="status">
          {expired
            ? "This request expired and was not run. Ask the agent to try again."
            : `This request is ${approval.status}.`}
        </p>
      )}
    </section>
  );
}

function tryJson(value: string): unknown {
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}
