"use client";

import { HubChrome } from "@/components/shell/hub-chrome";
import { PageFrame } from "@/components/ui/page-frame";
import { InboxPage } from "@/features/inbox/inbox-page";
import { MailPage } from "@/features/mail/mail-page";

export type NeedsYouHubProps = {
  section: "approvals" | "mail";
};

const TABS = [
  { id: "approvals", label: "Approvals", href: "/inbox" },
  { id: "mail", label: "Mail", href: "/mail" },
];

/** Approvals and a read-only mail list. Mail replies with drafts arrive later. */
export function NeedsYouHub({ section }: NeedsYouHubProps) {
  return (
    <PageFrame width={section === "mail" ? "full" : "chat"}>
      <HubChrome label="Needs you" tabs={TABS} />
      {section === "approvals" ? <InboxPage embedded /> : <MailPage embedded />}
    </PageFrame>
  );
}
