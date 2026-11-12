const ENTITIES: Record<string, string> = {
  "&amp;": "&",
  "&lt;": "<",
  "&gt;": ">",
  "&quot;": '"',
  "&#39;": "'",
  "&apos;": "'",
  "&nbsp;": " ",
};

/** Gmail snippets arrive HTML-escaped. Decode to plain text only; never render as markup. */
export function decodeSnippet(value: string): string {
  return value
    .replace(/&(amp|lt|gt|quot|#39|apos|nbsp);/g, (m) => ENTITIES[m] ?? m)
    .replace(/&#(\d+);/g, (m, code: string) => {
      const n = Number(code);
      return n > 0 && n < 0x110000 ? String.fromCodePoint(n) : m;
    });
}

/** "Ana Lee <ana@x.com>" → { name: "Ana Lee", address: "ana@x.com" }. */
export function parseSender(from: string): { name: string; address: string } {
  const match = from.match(/^\s*"?([^"<]*?)"?\s*<([^>]+)>\s*$/);
  if (match) {
    const address = match[2].trim();
    return { name: match[1].trim() || address, address };
  }
  const bare = from.trim();
  return { name: bare, address: bare.includes("@") ? bare : "" };
}

export function formatReceived(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}
