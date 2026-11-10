/** Sample social connection state. Drafts are preview copy and are never published. */

export type Draft = {
  id: string;
  title: string;
  body: string;
  updatedAt: string;
};

export type SocialPreview = {
  connected: boolean;
  displayName: string;
  drafts: Draft[];
};

export const linkedinPreview: SocialPreview = {
  connected: true,
  displayName: "AURA Preview",
  drafts: [
    {
      id: "li-1",
      title: "Sample: what this week is for",
      body: "A short preview post about keeping one list of open work and one place for decisions. This text stays in AURA until a real LinkedIn connection exists.",
      updatedAt: "2026-11-10T09:00:00.000Z",
    },
    {
      id: "li-2",
      title: "Sample: note on focus",
      body: "Preview draft. It describes a quiet morning block for writing and review. Publishing is not connected, so this cannot leave the workspace.",
      updatedAt: "2026-11-08T15:20:00.000Z",
    },
    {
      id: "li-3",
      title: "Sample: a question for peers",
      body: "Sample question: how do you keep follow-ups from slipping into chat threads? Shown here only so the draft list can be previewed.",
      updatedAt: "2026-11-06T11:45:00.000Z",
    },
    {
      id: "li-4",
      title: "Sample: project snapshot",
      body: "Three sentences of sample status: the outline is done, the review is Thursday, and the notes live in the workspace. Not a live LinkedIn post.",
      updatedAt: "2026-11-04T08:10:00.000Z",
    },
    {
      id: "li-5",
      title: "Sample: reading list",
      body: "A preview of a reading note. Titles are fictional. Use Preview draft to read the full copy. There is no publish action on this page.",
      updatedAt: "2026-11-02T17:30:00.000Z",
    },
    {
      id: "li-6",
      title: "Sample: closing the loop",
      body: "Sample closing note thanking a collaborator. The display name on this channel is a preview profile, not an authorized LinkedIn account.",
      updatedAt: "2026-10-30T13:05:00.000Z",
    },
  ],
};

export const facebookPreview: SocialPreview = {
  connected: true,
  displayName: "AURA Preview Page",
  drafts: [
    {
      id: "fb-1",
      title: "Sample: page update",
      body: "Preview page post. It announces a sample office hour next week. Facebook publishing is not available, so this remains a draft in AURA.",
      updatedAt: "2026-11-10T10:20:00.000Z",
    },
    {
      id: "fb-2",
      title: "Sample: photo caption",
      body: "Caption for a sample photo that is not attached. The words are here so you can read the draft in Content Studio before any integration exists.",
      updatedAt: "2026-11-09T12:00:00.000Z",
    },
    {
      id: "fb-3",
      title: "Sample: event reminder",
      body: "Reminder copy for a fictional community meetup. Date, place, and host are placeholders. This preview does not create a Facebook event.",
      updatedAt: "2026-11-07T18:40:00.000Z",
    },
    {
      id: "fb-4",
      title: "Sample: thank-you note",
      body: "A short thank-you kept as a draft. The connected flag on this page describes the sample page, not a live OAuth grant.",
      updatedAt: "2026-11-05T09:15:00.000Z",
    },
    {
      id: "fb-5",
      title: "Sample: weekend hours",
      body: "Preview of weekend hours for the sample page. Readers of this modal are looking at local mock data only.",
      updatedAt: "2026-11-03T16:50:00.000Z",
    },
    {
      id: "fb-6",
      title: "Sample: question of the day",
      body: "Sample prompt asking what people are reading. It is listed so the Facebook draft list paginates. Nothing is sent to Facebook.",
      updatedAt: "2026-11-01T11:25:00.000Z",
    },
  ],
};
