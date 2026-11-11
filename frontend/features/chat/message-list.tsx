import { Spinner } from "@/components/ui/spinner";
import { ApprovalCard } from "@/features/approvals/approval-card";
import { SaveMemoryChip, UsedMemoryChips } from "@/features/memory/memory-chips";
import type {
  Approval,
  ApprovalDecisionResponse,
  MemoryProposal,
  UsedMemory,
} from "@/lib/api/types";
import { AssistantMarkdown } from "./assistant-markdown";
import type { TrailStep } from "./run-trail";
import { StepTrail } from "./step-trail";

export type ChatBubble = {
  id: string;
  role: "user" | "assistant";
  content: string;
  pending?: boolean;
  incomplete?: boolean;
  /** Tool steps the agent took for this answer, filled live from run events. */
  steps?: TrailStep[];
  /** The owner pressed Stop; `content` holds the progress summary. */
  stopped?: boolean;
  /** Run this answer belongs to (needed to continue it after an approval). */
  runId?: string;
  /** Set while the run is paused for the owner's decision. */
  approval?: Approval;
  memoryProposal?: MemoryProposal;
  usedMemories?: UsedMemory[];
};

export type MessageListProps = {
  messages: ChatBubble[];
  onApprovalDecided?: (messageId: string, response: ApprovalDecisionResponse) => void;
  onApprovalReplaced?: (messageId: string, replacement: Approval) => void;
};

export function MessageList({ messages, onApprovalDecided, onApprovalReplaced }: MessageListProps) {
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
            {!mine && message.steps && message.steps.length > 0 ? (
              <StepTrail steps={message.steps} pending={Boolean(message.pending)} />
            ) : null}
            {message.pending && !message.content ? (
              <span className="inline-flex items-center gap-2 text-[var(--muted)]">
                <Spinner size="sm" />
                Your agent is working…
              </span>
            ) : mine ? (
              message.content
            ) : message.content ? (
              <AssistantMarkdown content={message.content} />
            ) : message.approval ? (
              <p>I need your approval before I continue.</p>
            ) : null}
            {message.approval ? (
              <div className="mt-3">
                <ApprovalCard
                  approval={message.approval}
                  onDecided={(response) => onApprovalDecided?.(message.id, response)}
                  onReplaced={(replacement) => onApprovalReplaced?.(message.id, replacement)}
                />
              </div>
            ) : null}
            {message.memoryProposal ? <SaveMemoryChip proposal={message.memoryProposal} /> : null}
            {message.usedMemories ? <UsedMemoryChips items={message.usedMemories} /> : null}
            {message.stopped ? (
              <p className="mt-2 text-xs text-[var(--muted)]">Stopped at your request.</p>
            ) : null}
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
