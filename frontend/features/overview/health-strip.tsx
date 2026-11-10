import Link from "next/link";
import { capabilities } from "@/lib/capabilities";
import type { StatusPayload } from "@/lib/api/types";
import { Badge, type BadgeTone } from "@/components/ui/badge";

export type HealthStripProps = {
  status: StatusPayload | null;
  statusUnavailable: boolean;
};

type ChannelChip = {
  key: string;
  label: string;
  href: string;
  statusLabel: string;
  tone: BadgeTone;
};

function telegramChip(status: StatusPayload | null, statusUnavailable: boolean): ChannelChip {
  const href = "/connections/telegram";
  if (statusUnavailable || !status) {
    return {
      key: "telegram",
      label: "Telegram",
      href,
      statusLabel: "Unavailable",
      tone: "warning",
    };
  }
  const { configured, managed, runtime } = status.telegram;
  if (!configured) {
    return {
      key: "telegram",
      label: "Telegram",
      href,
      statusLabel: "Not configured",
      tone: "neutral",
    };
  }
  if (managed) {
    return {
      key: "telegram",
      label: "Telegram",
      href,
      statusLabel: runtime === "running" ? "Managed · running" : "Managed",
      tone: "success",
    };
  }
  return {
    key: "telegram",
    label: "Telegram",
    href,
    statusLabel: "Configured",
    tone: "accent",
  };
}

function previewChip(
  key: string,
  label: string,
  href: string,
  mode: (typeof capabilities)[keyof typeof capabilities],
): ChannelChip {
  return {
    key,
    label,
    href,
    statusLabel: mode === "mock" ? "Preview" : "API",
    tone: mode === "mock" ? "neutral" : "accent",
  };
}

export function HealthStrip({ status, statusUnavailable }: HealthStripProps) {
  const chips: ChannelChip[] = [
    telegramChip(status, statusUnavailable),
    previewChip("google", "Google", "/connections/google", capabilities.google),
    previewChip("linkedin", "LinkedIn", "/connections/linkedin", capabilities.linkedin),
    previewChip("facebook", "Facebook", "/connections/facebook", capabilities.facebook),
  ];

  return (
    <section
      className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3 sm:px-5"
      aria-label="Connection health"
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-[var(--ink)]">Connections</h2>
        <Link
          href="/connections"
          className="text-xs font-medium text-[var(--accent)] hover:underline"
        >
          All channels
        </Link>
      </div>
      <ul className="flex flex-wrap gap-2">
        {chips.map((chip) => (
          <li key={chip.key}>
            <Link
              href={chip.href}
              className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--canvas)] px-3 py-1.5 text-xs transition hover:border-[var(--accent)]/40"
            >
              <span className="font-medium text-[var(--ink)]">{chip.label}</span>
              <Badge tone={chip.tone}>{chip.statusLabel}</Badge>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
