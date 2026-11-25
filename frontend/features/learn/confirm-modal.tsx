"use client";

import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";

export function ConfirmModal({
  open,
  title,
  message,
  confirmLabel,
  busy,
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  busy?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <p className="text-sm text-[var(--muted)]">{message}</p>
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="secondary" className="min-h-11" onClick={onClose}>
          Cancel
        </Button>
        <Button variant="danger" className="min-h-11" loading={busy} onClick={onConfirm}>
          {confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}
