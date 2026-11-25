"use client";

import { HubChrome } from "@/components/shell/hub-chrome";
import { PageFrame } from "@/components/ui/page-frame";
import { InboxPage } from "@/features/inbox/inbox-page";
import { MailPage } from "@/features/mail/mail-page";

export type NeedsYouHubProps = {
  section: "approvals" | "mail";
};

const MAIL_TABS = [
  { id: "approvals", label: "Needs you", href: "/inbox" },
  { id: "mail", label: "All mail", href: "/mail" },
];

/**
 * Needs you has one tab row (Approvals, Suggestions, Mail replies, Done). The full mail list is
 * a separate screen reached from Mail replies, with a way back.
 */
export function NeedsYouHub({ section }: NeedsYouHubProps) {
  if (section === "mail") {
    return (
      <PageFrame width="full">
        <HubChrome label="Needs you" tabs={MAIL_TABS} />
        <MailPage embedded />
      </PageFrame>
    );
  }
  return (
    <PageFrame width="chat">
      <InboxPage />
    </PageFrame>
  );
}
