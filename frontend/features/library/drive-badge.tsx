import { StatusChip } from "@/components/ui/status-chip";

/** Small "In Drive" chip. Renders nothing unless the API gave a Drive link. */
export function DriveBadge({
  driveUrl,
  withLink = false,
}: {
  driveUrl: string | null | undefined;
  /** Only use inside non-interactive areas (never inside a button). */
  withLink?: boolean;
}) {
  if (!driveUrl) return null;
  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <StatusChip tone="success">In Drive</StatusChip>
      {withLink ? (
        <a
          href={driveUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex min-h-11 items-center text-sm font-medium text-[var(--accent)] underline sm:min-h-0"
        >
          Open in Drive
        </a>
      ) : null}
    </span>
  );
}
