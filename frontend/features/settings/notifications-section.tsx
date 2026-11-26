"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import {
  getNotificationPrefs,
  isEnforced,
  isEnforcedChild,
  patchNotificationPrefs,
  type NotificationPrefs,
  type NotificationPrefsResponse,
} from "@/lib/api/profile";

const ALL_KEYS = [
  "channels.in_app",
  "channels.telegram",
  "daily_briefing",
  "reminders",
  "learning_daily",
  "reading_daily",
  "diary_nudge",
  "habit_nudge",
  "money_alerts",
  "daily_wrapup",
  "wrapup_time",
  "learning_time",
  "reading_time",
  "diary_time",
  "habit_time",
  "money_time",
  "quiet_hours",
];

function stripEnforced(response: NotificationPrefsResponse): NotificationPrefs {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { enforced, ...prefs } = response;
  return prefs;
}

export function NotificationsSection() {
  const { toast } = useToast();
  const [enforced, setEnforced] = useState<string[]>([]);
  const [saved, setSaved] = useState<NotificationPrefs | null>(null);
  const [draft, setDraft] = useState<NotificationPrefs | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const response = await getNotificationPrefs();
      setEnforced(response.enforced ?? []);
      const prefs = stripEnforced(response);
      setSaved(prefs);
      setDraft(prefs);
    } catch (err) {
      setLoadError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading && !draft) {
    return (
      <Card title="Notifications">
        <div
          className="flex flex-col gap-3"
          role="status"
          aria-label="Loading notification settings"
        >
          <Skeleton heightClass="h-11" className="w-full" />
          <Skeleton heightClass="h-11" className="w-full" />
          <Skeleton heightClass="h-11" className="w-full" />
        </div>
      </Card>
    );
  }

  if (loadError || !draft || !saved) {
    return (
      <Card title="Notifications">
        <div className="flex flex-wrap items-center gap-3 text-sm" role="alert">
          <span className="text-[var(--danger)]">
            Could not load notification settings: {loadError ?? "no data"}
          </span>
          <Button size="sm" variant="secondary" onClick={() => void load()}>
            Try again
          </Button>
        </div>
      </Card>
    );
  }

  const prefs = draft;
  const dirty = JSON.stringify(draft) !== JSON.stringify(saved);
  const showChannel = (key: "in_app" | "telegram") => isEnforcedChild(enforced, "channels", key);
  const hiddenSome = ALL_KEYS.some((key) =>
    key.includes(".")
      ? !isEnforcedChild(enforced, key.split(".")[0], key.split(".")[1])
      : !isEnforced(enforced, key),
  );
  const anyShown = ALL_KEYS.some((key) =>
    key.includes(".")
      ? isEnforcedChild(enforced, key.split(".")[0], key.split(".")[1])
      : isEnforced(enforced, key),
  );

  function update(patch: Partial<NotificationPrefs>) {
    setDraft((prev) => (prev ? { ...prev, ...patch } : prev));
    setSaveError(null);
  }

  async function onSave() {
    if (!draft || !saved) return;
    setSaving(true);
    setSaveError(null);
    const patch: Record<string, unknown> = {};
    for (const key of Object.keys(draft) as (keyof NotificationPrefs)[]) {
      if (JSON.stringify(draft[key]) !== JSON.stringify(saved[key])) patch[key] = draft[key];
    }
    try {
      const response = await patchNotificationPrefs(patch as Partial<NotificationPrefs>);
      setEnforced(response.enforced ?? enforced);
      const next = stripEnforced(response);
      setSaved(next);
      setDraft(next);
      toast("Notification settings saved.", "success");
    } catch (err) {
      setSaveError(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  if (!anyShown) {
    return (
      <Card title="Notifications">
        <EmptyState
          compact
          title="Nothing to adjust yet"
          description="Compass does not send reminders you can tune yet. When it does, the options show up here."
        />
      </Card>
    );
  }

  const channelRows: ReactNode[] = [];
  if (showChannel("in_app")) {
    channelRows.push(
      <Toggle
        key="in_app"
        label="In Compass"
        hint="The bell at the top of the page."
        checked={prefs.channels.in_app}
        onChange={(v) => update({ channels: { ...prefs.channels, in_app: v } })}
      />,
    );
  }
  if (showChannel("telegram")) {
    channelRows.push(
      <Toggle
        key="telegram"
        label="Telegram"
        hint="Messages from Compass in your connected chat."
        checked={prefs.channels.telegram}
        onChange={(v) => update({ channels: { ...prefs.channels, telegram: v } })}
      />,
    );
  }

  const gentle: ReactNode[] = [];
  const flag = (
    key:
      | "daily_briefing"
      | "reminders"
      | "learning_daily"
      | "reading_daily"
      | "diary_nudge"
      | "habit_nudge"
      | "money_alerts"
      | "daily_wrapup",
    label: string,
    hint: string,
    timeKey?:
      "learning_time" | "reading_time" | "diary_time" | "habit_time" | "money_time" | "wrapup_time",
  ) => {
    if (!isEnforced(enforced, key)) return;
    gentle.push(
      <div key={key}>
        <Toggle
          label={label}
          hint={hint}
          checked={prefs[key]}
          onChange={(v) => update({ [key]: v })}
        />
        {timeKey && isEnforced(enforced, timeKey) && prefs[key] ? (
          <TimeField
            label={`${label} time`}
            value={prefs[timeKey]}
            onChange={(v) => update({ [timeKey]: v })}
          />
        ) : null}
      </div>,
    );
  };
  flag("daily_briefing", "Daily briefing", "A short summary of your day each morning.");
  flag("reminders", "Reminders", "Tasks and events that are about to start.");
  flag("learning_daily", "Words to review", "A nudge when you have words due.", "learning_time");
  flag("reading_daily", "Reading", "A reminder for your next passage.", "reading_time");
  flag("diary_nudge", "Diary", "A gentle prompt to write today's entry.", "diary_time");
  flag(
    "habit_nudge",
    "Habits",
    "Habits still open today, and any missed three days running.",
    "habit_time",
  );
  flag(
    "money_alerts",
    "Money alerts",
    "Budget categories near their limit and bills due soon.",
    "money_time",
  );
  flag(
    "daily_wrapup",
    "Evening wrap-up",
    "How your day went, and an offer to carry unfinished tasks to tomorrow.",
    "wrapup_time",
  );

  return (
    <div className="flex flex-col gap-4">
      {hiddenSome ? (
        <Banner tone="info" role="status">
          Some options are not available yet, so they are hidden instead of pretending to work.
        </Banner>
      ) : null}
      {channelRows.length > 0 ? (
        <Card title="Where to tell you">
          <div className="flex flex-col divide-y divide-[var(--border)]">{channelRows}</div>
        </Card>
      ) : null}
      {gentle.length > 0 ? (
        <Card title="What to tell you">
          <div className="flex flex-col divide-y divide-[var(--border)]">{gentle}</div>
        </Card>
      ) : null}
      {isEnforced(enforced, "quiet_hours") ? (
        <Card title="Quiet hours">
          <Toggle
            label="Stay quiet at night"
            hint="No notifications between these times."
            checked={prefs.quiet_hours.enabled}
            onChange={(v) => update({ quiet_hours: { ...prefs.quiet_hours, enabled: v } })}
          />
          {prefs.quiet_hours.enabled ? (
            <div className="mt-2 flex flex-wrap gap-4">
              <TimeField
                label="From"
                value={prefs.quiet_hours.start}
                onChange={(v) => update({ quiet_hours: { ...prefs.quiet_hours, start: v } })}
              />
              <TimeField
                label="Until"
                value={prefs.quiet_hours.end}
                onChange={(v) => update({ quiet_hours: { ...prefs.quiet_hours, end: v } })}
              />
            </div>
          ) : null}
        </Card>
      ) : null}
      {saveError ? (
        <p className="text-sm text-[var(--danger)]" role="alert">
          Could not save: {saveError}
        </p>
      ) : null}
      <div>
        <Button onClick={() => void onSave()} disabled={!dirty} loading={saving}>
          Save changes
        </Button>
      </div>
    </div>
  );
}

function Toggle({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex min-h-[48px] cursor-pointer items-center justify-between gap-4 py-2">
      <span className="min-w-0">
        <span className="block text-sm font-medium text-[var(--ink)]">{label}</span>
        {hint ? (
          <span className="block text-[length:var(--text-caption)] text-[var(--muted)]">
            {hint}
          </span>
        ) : null}
      </span>
      <input
        type="checkbox"
        role="switch"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-5 w-5 shrink-0 accent-[var(--accent)]"
      />
    </label>
  );
}

function TimeField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const id = `time-${label.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <div className="flex items-center gap-3 pb-2 pl-0">
      <label htmlFor={id} className="text-sm text-[var(--muted)]">
        {label}
      </label>
      <Input
        id={id}
        type="time"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="min-h-[44px] w-32"
      />
    </div>
  );
}
