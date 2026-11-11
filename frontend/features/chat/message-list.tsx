import { Spinner } from "@/components/ui/spinner";
import { AssistantMarkdown } from "./assistant-markdown";

export type ChatBubble = {
  id: string;
  role: "user" | "assistant";
  content: string;
  pending?: boolean;
  incomplete?: boolean;
};

export function MessageList({ messages }: { messages: ChatBubble[] }) {
  return (
    <ol className="flex flex-col gap-3" aria-live="polite">
      {messages.map((message) => {
        const mine = message.role === "user";
        return (
          <li
            key={message.id}
            className={`max-w-[85%] rounded-[var(--radius)] px-4 py-3 text-sm leading-6 break-words ${
              mine
                ? "ml-auto bg-[var(--accent)] text-white whitespace-pre-wrap"
                : "border border-[var(--border)] bg-[var(--canvas)] text-[var(--ink)]"
            }`}
          >
            {message.pending && !message.content ? (
              <span className="inline-flex items-center gap-2 text-[var(--muted)]">
                <Spinner size="sm" />
                Your agent is working…
              </span>
            ) : mine ? (
              message.content
            ) : (
              <AssistantMarkdown content={message.content} />
            )}
            {message.incomplete ? (
              <p className={`mt-2 text-xs ${mine ? "text-white/80" : "text-[var(--danger)]"}`}>
                The reply stopped before it finished.
              </p>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
