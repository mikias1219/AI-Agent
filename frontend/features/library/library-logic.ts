import type { Mood, Note } from "@/lib/api/notes";

export const MAX_TAGS = 10;
export const MAX_TAG_LENGTH = 30;
export const MAX_FILE_BYTES = 5 * 1024 * 1024;
export const STORAGE_CAP_BYTES = 200 * 1024 * 1024;

export const ALLOWED_MIMES = [
  "image/png",
  "image/jpeg",
  "image/webp",
  "image/gif",
  "application/pdf",
  "text/plain",
  "text/markdown",
  "text/csv",
  "application/json",
] as const;

const IMAGE_MIMES = new Set(ALLOWED_MIMES.filter((m) => m.startsWith("image/")));

const EXT_MIME: Record<string, string> = {
  md: "text/markdown",
  markdown: "text/markdown",
  csv: "text/csv",
  txt: "text/plain",
  json: "application/json",
  pdf: "application/pdf",
};

export function normaliseTag(raw: string): string {
  return raw.trim().replace(/^#/, "").trim().toLowerCase().slice(0, MAX_TAG_LENGTH);
}

/** Add tags (comma separated allowed), deduplicated, lowercase, capped at MAX_TAGS. */
export function addTags(existing: string[], raw: string): string[] {
  const next = [...existing];
  for (const part of raw.split(",")) {
    const tag = normaliseTag(part);
    if (tag && !next.includes(tag) && next.length < MAX_TAGS) next.push(tag);
  }
  return next;
}

export function isImageMime(mime: string): boolean {
  return IMAGE_MIMES.has(mime as (typeof ALLOWED_MIMES)[number]);
}

/** Browsers often leave File.type empty for .md or .csv; fall back to the extension. */
export function resolveMime(name: string, declared: string): string {
  if (declared) return declared;
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  return EXT_MIME[ext] ?? "";
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(bytes < 10 * 1024 ? 1 : 0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export type FileCheck = { ok: true; mime: string } | { ok: false; error: string };

export function validateUpload(file: { name: string; type: string; size: number }): FileCheck {
  const mime = resolveMime(file.name, file.type);
  if (mime === "image/svg+xml") {
    return { ok: false, error: "SVG images are not allowed. Use PNG, JPEG, WebP or GIF." };
  }
  if (!(ALLOWED_MIMES as readonly string[]).includes(mime)) {
    return {
      ok: false,
      error:
        "This file type is not supported. Use an image, PDF, text, Markdown, CSV or JSON file.",
    };
  }
  if (file.size === 0) return { ok: false, error: "This file is empty." };
  if (file.size > MAX_FILE_BYTES) {
    return { ok: false, error: `Too large (${formatBytes(file.size)}). The limit is 5 MB.` };
  }
  return { ok: true, mime };
}

/** Strip the `data:...;base64,` prefix produced by FileReader.readAsDataURL. */
export function dataUrlToBase64(dataUrl: string): string {
  const i = dataUrl.indexOf(",");
  return i === -1 ? dataUrl : dataUrl.slice(i + 1);
}

export function storagePercent(bytes: number, cap: number = STORAGE_CAP_BYTES): number {
  if (cap <= 0 || bytes <= 0) return 0;
  return Math.min(100, Math.round((bytes / cap) * 100));
}

export type MonthGroup<T> = { key: string; label: string; items: T[] };

/** Group diary entries (already newest first) by month of entry_date. */
export function groupDiaryByMonth(entries: Note[]): MonthGroup<Note>[] {
  const groups: MonthGroup<Note>[] = [];
  for (const entry of entries) {
    const date = entry.entry_date ?? entry.created_at.slice(0, 10);
    const key = date.slice(0, 7);
    let group = groups[groups.length - 1];
    if (!group || group.key !== key) {
      group = { key, label: monthLabel(key), items: [] };
      groups.push(group);
    }
    group.items.push(entry);
  }
  return groups;
}

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export function monthLabel(key: string): string {
  const [y, m] = key.split("-");
  const name = MONTHS[Number(m) - 1];
  return name ? `${name} ${y}` : key;
}

export function todayIso(now: Date = new Date()): string {
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function formatEntryDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso;
  return new Date(y, m - 1, d).toLocaleDateString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

export function relativeTime(iso: string, now: number = Date.now()): string {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return "";
  const sec = Math.max(0, Math.round((now - t) / 1000));
  if (sec < 60) return "just now";
  const min = Math.round(sec / 60);
  if (min < 60) return `${min} min ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr} h ago`;
  const day = Math.round(hr / 24);
  if (day < 30) return `${day} d ago`;
  return new Date(t).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** Plain-text preview: strips common markdown marks and collapses whitespace. */
export function previewText(body: string, max = 160): string {
  const plain = body
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/^\s*[-*>#]+\s+/gm, "")
    .replace(/[*_`~]+/g, "")
    .replace(/\s+/g, " ")
    .trim();
  return plain.length > max ? `${plain.slice(0, max).trimEnd()}…` : plain;
}

export const MOODS: { value: Mood; label: string }[] = [
  { value: "great", label: "Great" },
  { value: "good", label: "Good" },
  { value: "okay", label: "Okay" },
  { value: "low", label: "Low" },
  { value: "bad", label: "Bad" },
];

export function askAuraHref(prompt: string): string {
  return `/chat?q=${encodeURIComponent(prompt)}`;
}

export function sameTags(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((t, i) => t === b[i]);
}
