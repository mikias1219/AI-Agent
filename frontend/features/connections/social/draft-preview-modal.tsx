"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import type { Draft } from "@/lib/mocks/social";
import { formatWhen } from "../format";

export type DraftPreviewModalProps = {
  open: boolean;
  draft: Draft | null;
  channelLabel: string;
  onClose: () => void;
};

export function DraftPreviewModal({
  open,
  draft,
  channelLabel,
  onClose,
}: DraftPreviewModalProps) {
  return (
    <Modal open={open} onClose={onClose} title="Content Studio">
      {draft ? (
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="neutral">Preview</Badge>
            <span className="text-xs text-[var(--muted)]">{channelLabel}</span>
          </div>
          <div>
            <h3 className="text-base font-semibold text-[var(--ink)]">{draft.title}</h3>
            <p className="mt-1 text-xs text-[var(--muted)]">Updated {formatWhen(draft.updatedAt)}</p>
          </div>
          <p className="text-sm leading-6 whitespace-pre-wrap text-[var(--ink)]">{draft.body}</p>
          <p className="text-sm text-[var(--muted)]">
            This is a draft preview. AURA will not post it to {channelLabel}. Publishing is not
            connected.
          </p>
          <div className="flex justify-end">
            <Button variant="secondary" size="sm" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      ) : null}
    </Modal>
  );
}
