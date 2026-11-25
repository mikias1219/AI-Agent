import type { LearnItem } from "@/lib/api/learn";

export const WORD_COUNTS = [3, 5, 8, 10] as const;
export const MAX_PLAN_ITEMS = 1500;

export const LANGUAGES: { code: string; label: string }[] = [
  { code: "en", label: "English" },
  { code: "es", label: "Spanish" },
  { code: "fr", label: "French" },
  { code: "de", label: "German" },
  { code: "it", label: "Italian" },
  { code: "pt", label: "Portuguese" },
  { code: "am", label: "Amharic" },
  { code: "ar", label: "Arabic" },
  { code: "ja", label: "Japanese" },
];

export function languageLabel(code: string): string {
  return LANGUAGES.find((l) => l.code === code)?.label ?? code;
}

/** Due items first by earliest due time, then lowest box; ties keep input order. */
export function orderReviewQueue(items: LearnItem[]): LearnItem[] {
  return items
    .map((item, index) => ({ item, index, t: Date.parse(item.next_review_at) }))
    .sort((a, b) => {
      const at = Number.isNaN(a.t) ? 0 : a.t;
      const bt = Number.isNaN(b.t) ? 0 : b.t;
      return at - bt || a.item.box - b.item.box || a.index - b.index;
    })
    .map((x) => x.item);
}

export type ReviewKeyAction = "reveal" | "again" | "know" | null;

/** Space reveals; 1 = again and 2 = know only once the meaning is shown. */
export function reviewKeyAction(key: string, revealed: boolean): ReviewKeyAction {
  if (key === " " || key === "Spacebar") return revealed ? null : "reveal";
  if (!revealed) return null;
  if (key === "1") return "again";
  if (key === "2") return "know";
  return null;
}

export function buildWordsPrompt(count: number, topic: string, languageLabelText: string): string {
  const t = topic.trim();
  const about = t ? ` about ${t}` : "";
  return `Teach me ${count} new ${languageLabelText} words${about}. For each give the meaning and one example sentence, then save them to my Learn list.`;
}

export function chatHref(prompt: string): string {
  return `/chat?q=${encodeURIComponent(prompt)}`;
}

export function levelText(box: number): string {
  const level = Math.min(5, Math.max(0, Math.round(box)));
  return `Level ${level} of 5`;
}

export function progressPercent(progress: number): number {
  if (!Number.isFinite(progress)) return 0;
  return Math.round(Math.min(1, Math.max(0, progress)) * 100);
}

/** Trim, drop blanks, drop consecutive duplicates, cap at MAX_PLAN_ITEMS. */
export function parseReferenceList(text: string): string[] {
  const out: string[] = [];
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) continue;
    if (out[out.length - 1] === line) continue;
    out.push(line);
    if (out.length >= MAX_PLAN_ITEMS) break;
  }
  return out;
}

export function explainPassageHref(reference: string): string {
  return chatHref(
    `Explain ${reference} in simple words: the main message, its context, and one way to apply it today.`,
  );
}

export function formatDue(iso: string, now: Date = new Date()): string {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return "Unknown";
  const diff = t - now.getTime();
  if (diff <= 0) return "Due now";
  const minutes = Math.round(diff / 60000);
  if (minutes < 60) return `In ${Math.max(1, minutes)} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `In ${hours} h`;
  const days = Math.round(hours / 24);
  return `In ${days} ${days === 1 ? "day" : "days"}`;
}

export function previewText(text: string, max = 80): string {
  const t = text.trim().replace(/\s+/g, " ");
  return t.length > max ? `${t.slice(0, max - 1)}…` : t;
}

/** Earliest future next_review_at among items, or null. */
export function nextDueIso(items: LearnItem[], now: Date = new Date()): string | null {
  let best: number | null = null;
  for (const i of items) {
    const t = Date.parse(i.next_review_at);
    if (!Number.isNaN(t) && t > now.getTime() && (best === null || t < best)) best = t;
  }
  return best === null ? null : new Date(best).toISOString();
}

/** Local calendar date as YYYY-MM-DD. */
export function localDateIso(d: Date = new Date()): string {
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}
