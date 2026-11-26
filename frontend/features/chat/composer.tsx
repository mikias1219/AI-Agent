"use client";

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { Send, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export type ComposerProps = {
  disabled?: boolean;
  sending?: boolean;
  stopping?: boolean;
  initialText?: string;
  /** When true, send `initialText` once as soon as the composer is ready (Chat `?q=`). */
  autoSend?: boolean;
  onSend: (text: string) => void;
  onStop?: () => void;
  /** Kept for callers; the page header owns "New chat" now. */
  onNewConversation?: () => void;
  /** Fired after auto-send so the page can clear `?q=` from the URL. */
  onAutoSent?: () => void;
};

export function Composer({
  disabled = false,
  sending = false,
  stopping = false,
  initialText = "",
  autoSend = false,
  onSend,
  onStop,
  onAutoSent,
}: ComposerProps) {
  const [text, setText] = useState(autoSend ? "" : initialText);
  const autoSent = useRef(false);
  const trimmed = text.trim();
  const blocked = disabled || sending;

  useEffect(() => {
    if (!autoSend || autoSent.current || disabled || sending) return;
    const prompt = initialText.trim();
    if (!prompt) return;
    autoSent.current = true;
    onSend(prompt);
    onAutoSent?.();
  }, [autoSend, disabled, sending, initialText, onSend, onAutoSent]);

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
    <form
      onSubmit={onSubmit}
      className="flex flex-col gap-1.5 border-t border-[var(--border)] pt-3"
    >
      <label className="sr-only" htmlFor="chat-input">
        Message your agent
      </label>
      <div className="flex items-end gap-2">
        <Textarea
          id="chat-input"
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={onKeyDown}
          maxLength={10000}
          rows={2}
          placeholder="Ask or tell Compass…"
          disabled={blocked}
          className="min-h-[44px] flex-1 resize-none rounded-lg"
        />
        {sending && onStop ? (
          <Button type="button" variant="secondary" onClick={onStop} disabled={stopping}>
            <Square className="size-4" aria-hidden />
            {stopping ? "Stopping…" : "Stop"}
          </Button>
        ) : (
          <Button type="submit" disabled={blocked || !trimmed} loading={sending}>
            <Send className="size-4" aria-hidden />
            Send
          </Button>
        )}
      </div>
      <p className="text-[length:var(--text-caption)] text-[var(--muted)]">
        Enter to send · Shift+Enter for a new line. Compass asks before anything is sent or changed.
      </p>
    </form>
  );
}
