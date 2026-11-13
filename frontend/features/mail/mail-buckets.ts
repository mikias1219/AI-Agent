import type { GoogleMessage } from "@/lib/api/google";

export type MailBucketId = "needs_reply" | "waiting" | "fyi" | "drafts" | "done";

export type MailBucket = {
  id: MailBucketId;
  label: string;
  messages: GoogleMessage[];
};

const NEEDS_REPLY = /\b(please reply|can you|could you|let me know|are you free|rsvp|confirm)\b/i;
const WAITING = /\b(waiting|pending|follow[- ]?up|circling back)\b/i;
const DRAFT = /\b(draft)\b/i;

/** Client-side AURA buckets from Gmail list metadata only — never invents messages. */
export function bucketMessages(messages: GoogleMessage[]): MailBucket[] {
  const buckets: Record<MailBucketId, GoogleMessage[]> = {
    needs_reply: [],
    waiting: [],
    fyi: [],
    drafts: [],
    done: [],
  };

  for (const message of messages) {
    const hay = `${message.subject} ${message.snippet}`;
    if (DRAFT.test(hay)) {
      buckets.drafts.push(message);
    } else if (NEEDS_REPLY.test(hay)) {
      buckets.needs_reply.push(message);
    } else if (WAITING.test(hay)) {
      buckets.waiting.push(message);
    } else {
      buckets.fyi.push(message);
    }
  }

  return [
    { id: "needs_reply", label: "Needs reply", messages: buckets.needs_reply },
    { id: "waiting", label: "Waiting on", messages: buckets.waiting },
    { id: "fyi", label: "FYI", messages: buckets.fyi },
    { id: "drafts", label: "Drafts by AURA", messages: buckets.drafts },
    { id: "done", label: "Done", messages: buckets.done },
  ];
}
