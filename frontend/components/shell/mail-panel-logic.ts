import { bucketMessages } from "@/features/mail/mail-buckets";
import type { GoogleMessage } from "@/lib/api/google";

/** How many recent messages look like they ask you something (shown on the top-bar icon). */
export function askingCount(messages: readonly GoogleMessage[]): number {
  return bucketMessages([...messages]).find((b) => b.id === "needs_reply")?.messages.length ?? 0;
}

export function gmailLink(id: string): string {
  return `https://mail.google.com/mail/u/0/#all/${encodeURIComponent(id)}`;
}
