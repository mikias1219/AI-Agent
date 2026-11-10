"use client";

import { useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Pagination } from "@/components/ui/pagination";
import { facebookPreview, linkedinPreview, type Draft } from "@/lib/mocks/social";
import { paginate } from "@/lib/pagination";
import { formatWhen } from "../format";
import { DraftPreviewModal } from "./draft-preview-modal";

const PAGE_SIZE = 4;

export type SocialChannelId = "linkedin" | "facebook";

const CHANNELS = {
  linkedin: {
    label: "LinkedIn",
    preview: linkedinPreview,
    summary: "Sample profile and draft posts. Preview does not publish to LinkedIn.",
  },
  facebook: {
    label: "Facebook",
    preview: facebookPreview,
    summary: "Sample page and draft posts. Preview does not publish to Facebook.",
  },
} as const;

export type SocialChannelPageProps = {
  channel: SocialChannelId;
};

export function SocialChannelPage({ channel }: SocialChannelPageProps) {
  const copy = CHANNELS[channel];
  const { preview } = copy;
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Draft | null>(null);
  const pageCount = Math.max(1, Math.ceil(preview.drafts.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount);
  const paged = paginate(preview.drafts, safePage, PAGE_SIZE);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-5">
      <header>
        <Link href="/connections" className="text-xs font-medium text-[var(--accent)] hover:underline">
          All channels
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <h1
            className="text-2xl font-semibold tracking-tight text-[var(--ink)]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {copy.label}
          </h1>
          <Badge tone="neutral">Preview</Badge>
        </div>
        <p className="mt-2 max-w-xl text-sm text-[var(--muted)]">{copy.summary}</p>
      </header>

      <section className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-5">
        <h2 className="text-base font-semibold text-[var(--ink)]">Connection</h2>
        <dl className="mt-4 space-y-3 text-sm">
          <div className="flex items-start justify-between gap-4">
            <dt className="text-[var(--muted)]">Account</dt>
            <dd className="text-right text-[var(--ink)]">
              {preview.connected ? preview.displayName : "Not connected"}
            </dd>
          </div>
          <div className="flex items-start justify-between gap-4">
            <dt className="text-[var(--muted)]">Link</dt>
            <dd className="text-right text-[var(--ink)]">
              {preview.connected ? "Sample link only" : "No account linked"}
            </dd>
          </div>
          <div className="flex items-start justify-between gap-4">
            <dt className="text-[var(--muted)]">Drafts</dt>
            <dd className="text-right text-[var(--ink)]">{preview.drafts.length}</dd>
          </div>
        </dl>
        <p className="mt-4 text-sm text-[var(--muted)]">
          Integration pending. This summary is preview data, not an OAuth connection, and there is
          no publish API on this page.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-base font-semibold text-[var(--ink)]">Drafts</h2>
        {preview.drafts.length === 0 ? (
          <EmptyState title="No drafts" description="Sample drafts will show here when present." />
        ) : (
          <>
            <ul className="flex flex-col gap-2">
              {paged.items.map((draft) => (
                <li
                  key={draft.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-[var(--ink)]">{draft.title}</p>
                    <p className="mt-1 text-xs text-[var(--muted)]">
                      Updated {formatWhen(draft.updatedAt)}
                    </p>
                  </div>
                  <Button variant="secondary" size="sm" onClick={() => setSelected(draft)}>
                    Preview draft
                  </Button>
                </li>
              ))}
            </ul>
            <Pagination
              page={paged.page}
              pageSize={paged.pageSize}
              total={paged.total}
              onPageChange={setPage}
            />
          </>
        )}
      </section>

      <DraftPreviewModal
        open={selected !== null}
        draft={selected}
        channelLabel={copy.label}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}
