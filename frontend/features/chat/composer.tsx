"use client";

import { FormEvent, KeyboardEvent, useState } from "react";
import { Send, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export type ComposerProps = {
  disabled?: boolean;
  sending?: boolean;
  stopping?: boolean;
  initialText?: string;
  onSend: (text: string) => void;
  onStop?: () => void;
  onNewConversation: () => void;
};

export function Composer({
  disabled = false,
  sending = false,
  stopping = false,
  initialText = "",
  onSend,
  onStop,
  onNewConversation,
}: ComposerProps) {
  const [text, setText] = useState(initialText);
  const trimmed = text.trim();
  const blocked = disabled || sending;

  function submit() {
    if (blocked || !trimmed) return;
    onSend(trimmed);
    setText("");
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    submit();
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-3 border-t border-[var(--border)] pt-4">
      <label className="sr-only" htmlFor="chat-input">
        Message your agent
      </label>
      <Textarea
        id="chat-input"
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={onKeyDown}
        maxLength={10000}
        rows={3}
        placeholder="Ask or tell AURA…"
        disabled={blocked}
        className="min-h-[72px] rounded-lg"
      />
      <div className="flex items-center justify-between gap-3">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onNewConversation}
          disabled={sending || disabled}
        >
          New conversation
        </Button>
        {sending && onStop ? (
          <Button type="button" variant="secondary" size="sm" onClick={onStop} disabled={stopping}>
            <Square className="size-4" aria-hidden />
            {stopping ? "Stopping…" : "Stop"}
          </Button>
        ) : (
          <Button type="submit" size="sm" disabled={blocked || !trimmed} loading={sending}>
            <Send className="size-4" aria-hidden />
            Send
          </Button>
        )}
      </div>
    </form>
  );
}
