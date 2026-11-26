"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent } from "react";
import { Button } from "@/components/ui/button";
import { Avatar } from "@/components/ui/avatar";
import { Card } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import {
  deletePhoto,
  getProfile,
  notifyProfileChanged,
  patchProfile,
  photoSrc,
  uploadPhoto,
  validatePhoto,
  type Profile,
} from "@/lib/api/profile";

const BIO_MAX = 500;

const LANGUAGES: { code: string; label: string }[] = [
  { code: "en", label: "English" },
  { code: "am", label: "Amharic" },
  { code: "ar", label: "Arabic" },
  { code: "de", label: "German" },
  { code: "es", label: "Spanish" },
  { code: "fr", label: "French" },
  { code: "it", label: "Italian" },
  { code: "pt", label: "Portuguese" },
  { code: "sw", label: "Swahili" },
];

function timeZones(current: string): string[] {
  let zones: string[] = [];
  try {
    const intl = Intl as unknown as { supportedValuesOf?: (key: string) => string[] };
    zones = intl.supportedValuesOf?.("timeZone") ?? [];
  } catch {
    zones = [];
  }
  if (!zones.includes("UTC")) zones = [...zones, "UTC"];
  if (current && !zones.includes(current)) zones = [current, ...zones];
  return zones;
}

type Draft = { name: string; bio: string; birthday: string; timezone: string; language: string };

function toDraft(profile: Profile): Draft {
  return {
    name: profile.name ?? "",
    bio: profile.bio ?? "",
    birthday: profile.birthday ?? "",
    timezone: profile.timezone ?? "",
    language: profile.language ?? "en",
  };
}

function memberSince(value: string): string {
  const date = new Date(value);
  if (!value || Number.isNaN(date.getTime())) return "Not on file";
  return date.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
}

export function ProfileSection() {
  const { toast } = useToast();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [errors, setErrors] = useState<Partial<Record<keyof Draft | "form", string>>>({});
  const [saving, setSaving] = useState(false);
  const [photoVersion, setPhotoVersion] = useState(() => Date.now());

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const next = await getProfile(true);
      setProfile(next);
      setDraft(toDraft(next));
    } catch (err) {
      setLoadError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const zones = useMemo(() => timeZones(profile?.timezone ?? ""), [profile?.timezone]);

  if (loading && !profile) {
    return (
      <Card title="Your details">
        <div className="flex flex-col gap-3" role="status" aria-label="Loading your profile">
          <Skeleton heightClass="h-16" className="w-full" />
          <Skeleton heightClass="h-10" className="w-full" />
          <Skeleton heightClass="h-10" className="w-full" />
        </div>
      </Card>
    );
  }

  if (loadError || !profile || !draft) {
    return (
      <Card title="Your details">
        <div className="flex flex-wrap items-center gap-3 text-sm" role="alert">
          <span className="text-[var(--danger)]">
            Could not load your profile: {loadError ?? "no data"}
          </span>
          <Button size="sm" variant="secondary" onClick={() => void load()}>
            Try again
          </Button>
        </div>
      </Card>
    );
  }

  const original = toDraft(profile);
  const dirty = (Object.keys(draft) as (keyof Draft)[]).some((key) => draft[key] !== original[key]);

  function set<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft((prev) => (prev ? { ...prev, [key]: value } : prev));
    setErrors((prev) => ({ ...prev, [key]: undefined, form: undefined }));
  }

  function validate(next: Draft): typeof errors {
    const found: typeof errors = {};
    if (!next.name.trim()) found.name = "Tell Compass what to call you.";
    if (next.bio.length > BIO_MAX) found.bio = `Keep it under ${BIO_MAX} characters.`;
    if (next.birthday && Number.isNaN(new Date(next.birthday).getTime())) {
      found.birthday = "Enter a valid date.";
    }
    if (next.birthday && new Date(next.birthday).getTime() > Date.now()) {
      found.birthday = "Your birthday cannot be in the future.";
    }
    if (!next.timezone || !zones.includes(next.timezone)) {
      found.timezone = "Pick a time zone from the list.";
    }
    return found;
  }

  async function onSave() {
    if (!draft) return;
    const found = validate(draft);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    setSaving(true);
    try {
      const next = await patchProfile({
        name: draft.name.trim(),
        bio: draft.bio,
        birthday: draft.birthday || null,
        timezone: draft.timezone,
        language: draft.language,
      });
      setProfile(next);
      setDraft(toDraft(next));
      notifyProfileChanged();
      toast("Profile saved.", "success");
    } catch (err) {
      const message = apiErrorMessage(err);
      const lower = message.toLowerCase();
      if (lower.includes("timezone") || lower.includes("time zone")) {
        setErrors({ timezone: message });
      } else {
        setErrors({ form: message });
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <PhotoCard
        profile={profile}
        photoVersion={photoVersion}
        onChanged={(next) => {
          setProfile(next);
          setPhotoVersion(Date.now());
          notifyProfileChanged();
        }}
      />

      <Card id="settings-profile-heading" title="About you">
        <form
          className="grid gap-4 sm:grid-cols-2"
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            void onSave();
          }}
        >
          <Field label="Name" htmlFor="profile-name" error={errors.name}>
            <Input
              id="profile-name"
              value={draft.name}
              autoComplete="name"
              maxLength={80}
              onChange={(e) => set("name", e.target.value)}
            />
          </Field>
          <Field label="Birthday" htmlFor="profile-birthday" error={errors.birthday}>
            <Input
              id="profile-birthday"
              type="date"
              value={draft.birthday}
              onChange={(e) => set("birthday", e.target.value)}
            />
          </Field>
          <Field label="Bio" htmlFor="profile-bio" error={errors.bio} className="sm:col-span-2">
            <Textarea
              id="profile-bio"
              rows={3}
              value={draft.bio}
              placeholder="A few words about you, so Compass knows who it is helping."
              onChange={(e) => set("bio", e.target.value)}
            />
            <p
              className={`text-right text-[length:var(--text-caption)] ${
                draft.bio.length > BIO_MAX ? "text-[var(--danger)]" : "text-[var(--muted)]"
              }`}
              aria-live="polite"
            >
              {draft.bio.length} / {BIO_MAX}
            </p>
          </Field>
          <Field label="Time zone" htmlFor="profile-timezone" error={errors.timezone}>
            <Input
              id="profile-timezone"
              list="profile-timezone-list"
              value={draft.timezone}
              autoComplete="off"
              placeholder="Start typing, for example Africa/Addis_Ababa"
              onChange={(e) => set("timezone", e.target.value)}
            />
            <datalist id="profile-timezone-list">
              {zones.map((zone) => (
                <option key={zone} value={zone} />
              ))}
            </datalist>
          </Field>
          <Field label="Language" htmlFor="profile-language">
            <Select
              id="profile-language"
              className="min-h-[44px]"
              value={draft.language}
              onChange={(e) => set("language", e.target.value)}
            >
              {LANGUAGES.some((l) => l.code === draft.language) ? null : (
                <option value={draft.language}>{draft.language}</option>
              )}
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.label}
                </option>
              ))}
            </Select>
          </Field>
          <dl className="grid gap-4 text-sm sm:col-span-2 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium text-[var(--muted)]">Email</dt>
              <dd className="mt-1 font-medium break-words text-[var(--ink)]">
                {profile.email || "Not on file"}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-[var(--muted)]">Member since</dt>
              <dd className="mt-1 font-medium text-[var(--ink)]">
                {memberSince(profile.member_since)}
              </dd>
            </div>
          </dl>
          {errors.form ? (
            <p className="text-sm text-[var(--danger)] sm:col-span-2" role="alert">
              Could not save: {errors.form}
            </p>
          ) : null}
          <div className="flex items-center gap-3 sm:col-span-2">
            <Button type="submit" disabled={!dirty} loading={saving}>
              Save changes
            </Button>
            {dirty && !saving ? (
              <button
                type="button"
                className="min-h-[44px] text-sm text-[var(--muted)] hover:text-[var(--ink)] hover:underline"
                onClick={() => {
                  setDraft(toDraft(profile));
                  setErrors({});
                }}
              >
                Discard changes
              </button>
            ) : null}
          </div>
        </form>
      </Card>
    </div>
  );
}

function PhotoCard({
  profile,
  photoVersion,
  onChanged,
}: {
  profile: Profile;
  photoVersion: number;
  onChanged: (next: Profile) => void;
}) {
  const { toast } = useToast();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState(false);

  useEffect(() => {
    if (!file) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function pick(candidate: File | undefined | null) {
    if (!candidate) return;
    const problem = validatePhoto(candidate);
    if (problem) {
      setError(problem);
      setFile(null);
      return;
    }
    setError(null);
    setFile(candidate);
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    pick(event.dataTransfer.files?.[0]);
  }

  async function save() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await uploadPhoto(file);
      const next = await getProfile(true);
      setFile(null);
      onChanged(next);
      toast("Photo saved.", "success");
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    setError(null);
    try {
      await deletePhoto();
      const next = await getProfile(true);
      setConfirmRemove(false);
      onChanged(next);
      toast("Photo removed.", "success");
    } catch (err) {
      setConfirmRemove(false);
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const shown = preview ?? photoSrc(profile, photoVersion);

  return (
    <Card title="Your photo">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`flex flex-wrap items-center gap-4 rounded-[var(--radius)] border border-dashed p-3 ${
          dragging ? "border-[var(--accent)] bg-[var(--accent-soft)]" : "border-[var(--border)]"
        }`}
      >
        <Avatar name={profile.name} src={shown} size="xl" />
        <div className="min-w-0 flex-1">
          <p className="text-sm text-[var(--ink)]">
            {file
              ? `Ready to save: ${file.name}`
              : "Drop a picture here, or choose one. PNG, JPEG or WebP, up to 1 MB."}
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <input
              ref={inputRef}
              id="profile-photo-input"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="sr-only"
              aria-label="Choose a profile picture"
              onChange={(e) => {
                pick(e.target.files?.[0]);
                e.target.value = "";
              }}
            />
            {file ? (
              <>
                <Button onClick={() => void save()} loading={busy}>
                  Save photo
                </Button>
                <Button variant="ghost" disabled={busy} onClick={() => setFile(null)}>
                  Cancel
                </Button>
              </>
            ) : (
              <>
                <Button variant="secondary" onClick={() => inputRef.current?.click()}>
                  Choose picture
                </Button>
                {profile.has_photo ? (
                  <Button variant="ghost" onClick={() => setConfirmRemove(true)}>
                    Remove photo
                  </Button>
                ) : null}
              </>
            )}
          </div>
          {error ? (
            <p className="mt-2 text-sm text-[var(--danger)]" role="alert">
              {error}
            </p>
          ) : null}
        </div>
      </div>
      <Modal
        open={confirmRemove}
        onClose={() => setConfirmRemove(false)}
        title="Remove your photo?"
      >
        <div className="flex flex-col gap-4">
          <p className="text-sm text-[var(--ink)]">
            Compass will show your initials instead. You can add a picture again any time.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setConfirmRemove(false)}>
              Keep photo
            </Button>
            <Button variant="danger" loading={busy} onClick={() => void remove()}>
              Remove photo
            </Button>
          </div>
        </div>
      </Modal>
    </Card>
  );
}
