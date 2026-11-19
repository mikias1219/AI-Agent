"use client";

import { HubChrome } from "@/components/shell/hub-chrome";
import { CalendarPage } from "@/features/calendar/calendar-page";
import { MailPage } from "@/features/mail/mail-page";

export type ScheduleHubProps = {
  section: "calendar" | "mail";
};

export function ScheduleHub({ section }: ScheduleHubProps) {
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-5">
      <HubChrome
        eyebrow="Schedule"
        title="Calendar and mail"
        description="Time and messages from your connected Google account — nothing invented."
        tabs={[
          { id: "calendar", label: "Calendar", href: "/calendar" },
          { id: "mail", label: "Mail", href: "/mail" },
        ]}
      />
      {section === "calendar" ? <CalendarPage embedded /> : <MailPage embedded />}
    </div>
  );
}
