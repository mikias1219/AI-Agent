const RUNTIME_LABEL: Record<string, string> = {
  unknown: "Not started",
  starting: "Starting",
  polling: "Listening",
  responding: "Answering",
  running: "Running",
  stopped: "Stopped",
  stale: "Heartbeat expired",
  error: "Connection error",
};

export function runtimeLabel(runtime: string): string {
  return RUNTIME_LABEL[runtime] ?? runtime;
}

export function formatWhen(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export function telegramEventLabel(event: string): string {
  switch (event) {
    case "telegram.reply_sent":
      return "Agent replied";
    case "telegram.reply_send_failed":
      return "Reply failed";
    case "telegram.ignored_no_reply":
      return "Skipped (no reply needed)";
    case "security.telegram_unauthorized_chat":
      return "Blocked unknown chat";
    case "telegram.identity_verified":
      return "Bot verified";
    default:
      return event.replaceAll("_", " ").replaceAll(".", " · ");
  }
}

export function telegramEventDetail(details: Record<string, unknown>): string {
  const parts: string[] = [];
  const preview =
    typeof details.preview === "string" && details.preview.trim() ? details.preview.trim() : "";
  if (preview) {
    parts.push(`"${preview}"`);
  } else if (details.chat_id !== undefined && details.chat_id !== null) {
    parts.push(`Chat ${String(details.chat_id)}`);
  }
  if (typeof details.username === "string" && details.username) {
    parts.push(`@${details.username}`);
  }
  if (typeof details.error_type === "string" && details.error_type) {
    parts.push(details.error_type);
  }
  return parts.join(" · ");
}
