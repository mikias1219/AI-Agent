import type { GoogleMessage } from "@/lib/api/google";

export type MailBucketId = "needs_reply" | "waiting" | "fyi";

export type MailBucket = {
  id: MailBucketId;
  label: string;
  messages: GoogleMessage[];
};

const NEEDS_REPLY = /\b(please reply|can you|could you|let me know|are you free|rsvp|confirm)\b/i;
const WAITING = /\b(waiting|pending|follow[- ]?up|circling back)\b/i;

/**
 * Quick filters: plain word matching on subject and preview, done in the browser.
 * This is not the agent reading the mail, so the UI must not present it as AURA's
 * judgement. Agent triage arrives with the "Mail replies" work (docs/TRANSFORMATION.md G2).
 */
export function bucketMessages(messages: GoogleMessage[]): MailBucket[] {
  const buckets: Record<MailBucketId, GoogleMessage[]> = {
    needs_reply: [],
    waiting: [],
    fyi: [],
  };

  for (const message of messages) {
    const hay = `${message.subject} ${message.snippet}`;
    if (NEEDS_REPLY.test(hay)) {
      buckets.needs_reply.push(message);
    } else if (WAITING.test(hay)) {
      buckets.waiting.push(message);
    } else {
      buckets.fyi.push(message);
    }
  }

  return [
    { id: "needs_reply", label: "Asks a question", messages: buckets.needs_reply },
    { id: "waiting", label: "Follow-ups", messages: buckets.waiting },
    { id: "fyi", label: "Everything else", messages: buckets.fyi },
  ];
}
