import { api, ApiError, apiUrl } from "./client";
import { invalidatePrefix } from "@/lib/client-cache/cache";

export type Profile = {
  name: string;
  email: string;
  timezone: string;
  language: string;
  bio: string;
  birthday: string | null;
  has_photo: boolean;
  photo_url: string | null;
  member_since: string;
};

export type ProfilePatch = Partial<
  Pick<Profile, "name" | "timezone" | "language" | "bio" | "birthday">
>;

export type QuietHours = { enabled: boolean; start: string; end: string };

export type NotificationPrefs = {
  channels: { in_app: boolean; telegram: boolean };
  daily_briefing: boolean;
  reminders: boolean;
  learning_daily: boolean;
  reading_daily: boolean;
  diary_nudge: boolean;
  daily_wrapup: boolean;
  wrapup_time: string;
  learning_time: string;
  reading_time: string;
  diary_time: string;
  quiet_hours: QuietHours;
};

/** The server also reports which keys really do something today. */
export type NotificationPrefsResponse = NotificationPrefs & { enforced: string[] };

export const PHOTO_MAX_BYTES = 1024 * 1024;
export const PHOTO_MIME_TYPES = ["image/png", "image/jpeg", "image/webp"] as const;

/** Window event the shell listens to so the avatar refreshes after a profile change. */
export const PROFILE_CHANGED_EVENT = "aura:profile-changed";

export function notifyProfileChanged(): void {
  if (typeof window !== "undefined") window.dispatchEvent(new Event(PROFILE_CHANGED_EVENT));
}

/** Returns a friendly message, or null when the file is acceptable. */
export function validatePhoto(file: { type: string; size: number }): string | null {
  if (!(PHOTO_MIME_TYPES as readonly string[]).includes(file.type)) {
    return "Use a PNG, JPEG or WebP picture.";
  }
  if (file.size <= 0) return "That file is empty. Pick another picture.";
  if (file.size > PHOTO_MAX_BYTES) {
    return "That picture is over 1 MB. Pick a smaller one.";
  }
  return null;
}

/** Reads a file as raw base64 (no data: prefix). */
export function fileToBase64(file: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Could not read that file."));
    reader.onload = () => {
      const result = typeof reader.result === "string" ? reader.result : "";
      const comma = result.indexOf(",");
      resolve(comma >= 0 ? result.slice(comma + 1) : result);
    };
    reader.readAsDataURL(file);
  });
}

/** Photo URL with a cache-busting version, or undefined when there is no photo. */
export function photoSrc(
  profile: Pick<Profile, "has_photo"> | null,
  version: number,
): string | undefined {
  return profile?.has_photo ? `${apiUrl("/profile/photo")}?v=${version}` : undefined;
}

/** Endpoints that answer 204 reach the shared client as an "unreadable response": that is success. */
async function noContent(run: () => Promise<unknown>): Promise<void> {
  try {
    await run();
  } catch (err) {
    if (!(err instanceof ApiError && err.status === 204)) throw err;
  }
  invalidatePrefix("GET:");
}

export function getProfile(bypassCache = false): Promise<Profile> {
  return api<Profile>("/profile", { bypassCache });
}

export function patchProfile(patch: ProfilePatch): Promise<Profile> {
  return api<Profile>("/profile", { method: "PATCH", body: JSON.stringify(patch) });
}

export async function uploadPhoto(file: File): Promise<{ photo_url: string }> {
  const problem = validatePhoto(file);
  if (problem) throw new Error(problem);
  const data_base64 = await fileToBase64(file);
  return api<{ photo_url: string }>("/profile/photo", {
    method: "PUT",
    body: JSON.stringify({ mime: file.type, data_base64 }),
  });
}

export function deletePhoto(): Promise<void> {
  return noContent(() => api<unknown>("/profile/photo", { method: "DELETE" }));
}

export function changePassword(current_password: string, new_password: string): Promise<void> {
  return noContent(() =>
    api<unknown>("/auth/password", {
      method: "POST",
      body: JSON.stringify({ current_password, new_password }),
    }),
  );
}

export function getNotificationPrefs(): Promise<NotificationPrefsResponse> {
  return api<NotificationPrefsResponse>("/profile/notifications", { bypassCache: true });
}

export function patchNotificationPrefs(
  patch: Partial<NotificationPrefs>,
): Promise<NotificationPrefsResponse> {
  return api<NotificationPrefsResponse>("/profile/notifications", {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

/** True when the key (or a dotted child such as `channels.telegram`) is listed as enforced. */
export function isEnforced(enforced: readonly string[], key: string): boolean {
  return enforced.some((entry) => entry === key || entry.startsWith(`${key}.`));
}

export function isEnforcedChild(
  enforced: readonly string[],
  parent: string,
  child: string,
): boolean {
  return enforced.includes(parent) || enforced.includes(`${parent}.${child}`);
}

export type PasswordStrength = { score: 0 | 1 | 2 | 3; label: string };

export const MIN_PASSWORD_LENGTH = 12;

export function passwordStrength(value: string): PasswordStrength {
  if (value.length === 0) return { score: 0, label: "" };
  if (value.length < MIN_PASSWORD_LENGTH) {
    return { score: 0, label: `Too short: ${MIN_PASSWORD_LENGTH - value.length} more to go.` };
  }
  const classes = [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/].filter((re) => re.test(value)).length;
  const long = value.length >= 16;
  const points = classes + (long ? 1 : 0);
  if (points >= 4) return { score: 3, label: "Strong." };
  if (points >= 3) return { score: 2, label: "Good. Adding length makes it stronger." };
  return { score: 1, label: "Okay. Mix in capitals, numbers or symbols." };
}
