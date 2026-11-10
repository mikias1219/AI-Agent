/** Sample Google rows for the preview channel. Not synced from a Google account. */

export type Message = {
  id: string;
  from: string;
  subject: string;
  snippet: string;
  receivedAt: string;
};

export type Event = {
  id: string;
  title: string;
  startsAt: string;
  location: string;
};

export type File = {
  id: string;
  name: string;
  kind: string;
  updatedAt: string;
};

export const googlePreview: {
  gmail: Message[];
  calendar: Event[];
  drive: File[];
} = {
  gmail: [
    {
      id: "gm-1",
      from: "studio@example.com",
      subject: "Sample: Monday briefing",
      snippet: "Preview inbox row. This message was not fetched from Gmail.",
      receivedAt: "2026-11-10T08:15:00.000Z",
    },
    {
      id: "gm-2",
      from: "notes@example.com",
      subject: "Sample: Draft reply waiting",
      snippet: "A placeholder thread so the list can be paged.",
      receivedAt: "2026-11-09T16:40:00.000Z",
    },
    {
      id: "gm-3",
      from: "calendar@example.com",
      subject: "Sample: Room hold confirmed",
      snippet: "Sample confirmation. No calendar account is connected.",
      receivedAt: "2026-11-09T11:05:00.000Z",
    },
    {
      id: "gm-4",
      from: "archive@example.com",
      subject: "Sample: Weekly reading",
      snippet: "Three links kept here only as preview copy.",
      receivedAt: "2026-11-08T19:22:00.000Z",
    },
    {
      id: "gm-5",
      from: "billing@example.com",
      subject: "Sample: Invoice 1042",
      snippet: "Fictional invoice summary for the Drive and mail preview.",
      receivedAt: "2026-11-08T09:10:00.000Z",
    },
    {
      id: "gm-6",
      from: "team@example.com",
      subject: "Sample: Notes from the review",
      snippet: "Action items shown so the Gmail tab has a second page.",
      receivedAt: "2026-11-07T15:48:00.000Z",
    },
    {
      id: "gm-7",
      from: "travel@example.com",
      subject: "Sample: Trip outline",
      snippet: "Dates and a city name. Nothing is booked.",
      receivedAt: "2026-11-06T13:02:00.000Z",
    },
    {
      id: "gm-8",
      from: "hello@example.com",
      subject: "Sample: Introduction",
      snippet: "A short sample greeting in the preview inbox.",
      receivedAt: "2026-11-05T10:30:00.000Z",
    },
    {
      id: "gm-9",
      from: "ops@example.com",
      subject: "Sample: Access checklist",
      snippet: "Preview checklist. Google sign-in is still pending.",
      receivedAt: "2026-11-04T18:16:00.000Z",
    },
    {
      id: "gm-10",
      from: "digest@example.com",
      subject: "Sample: Quiet afternoon digest",
      snippet: "Last preview row on this page of sample mail.",
      receivedAt: "2026-11-03T07:55:00.000Z",
    },
  ],
  calendar: [
    {
      id: "cal-1",
      title: "Sample: Focus block",
      startsAt: "2026-11-10T09:00:00.000Z",
      location: "Desk",
    },
    {
      id: "cal-2",
      title: "Sample: Project check-in",
      startsAt: "2026-11-10T14:00:00.000Z",
      location: "Room A",
    },
    {
      id: "cal-3",
      title: "Sample: Supplier call",
      startsAt: "2026-11-11T11:30:00.000Z",
      location: "Phone",
    },
    {
      id: "cal-4",
      title: "Sample: Design review",
      startsAt: "2026-11-12T15:00:00.000Z",
      location: "Studio",
    },
    {
      id: "cal-5",
      title: "Sample: Lunch hold",
      startsAt: "2026-11-12T12:00:00.000Z",
      location: "Nearby",
    },
    {
      id: "cal-6",
      title: "Sample: Planning hour",
      startsAt: "2026-11-13T08:30:00.000Z",
      location: "Desk",
    },
    {
      id: "cal-7",
      title: "Sample: Workshop",
      startsAt: "2026-11-13T16:00:00.000Z",
      location: "Hall",
    },
    {
      id: "cal-8",
      title: "Sample: Follow-up",
      startsAt: "2026-11-14T10:00:00.000Z",
      location: "Video",
    },
    {
      id: "cal-9",
      title: "Sample: Errand",
      startsAt: "2026-11-14T17:30:00.000Z",
      location: "Town",
    },
    {
      id: "cal-10",
      title: "Sample: Week close",
      startsAt: "2026-11-15T13:00:00.000Z",
      location: "Desk",
    },
  ],
  drive: [
    {
      id: "drv-1",
      name: "Sample brief.pdf",
      kind: "PDF",
      updatedAt: "2026-11-10T07:40:00.000Z",
    },
    {
      id: "drv-2",
      name: "Sample notes.docx",
      kind: "Document",
      updatedAt: "2026-11-09T12:15:00.000Z",
    },
    {
      id: "drv-3",
      name: "Sample budget.xlsx",
      kind: "Spreadsheet",
      updatedAt: "2026-11-08T09:05:00.000Z",
    },
    {
      id: "drv-4",
      name: "Sample shots",
      kind: "Folder",
      updatedAt: "2026-11-07T18:20:00.000Z",
    },
    {
      id: "drv-5",
      name: "Sample outline.md",
      kind: "Text",
      updatedAt: "2026-11-06T11:11:00.000Z",
    },
    {
      id: "drv-6",
      name: "Sample deck.pptx",
      kind: "Slides",
      updatedAt: "2026-11-05T16:45:00.000Z",
    },
    {
      id: "drv-7",
      name: "Sample references",
      kind: "Folder",
      updatedAt: "2026-11-04T08:25:00.000Z",
    },
    {
      id: "drv-8",
      name: "Sample logo.png",
      kind: "Image",
      updatedAt: "2026-11-03T14:55:00.000Z",
    },
    {
      id: "drv-9",
      name: "Sample checklist.txt",
      kind: "Text",
      updatedAt: "2026-11-02T10:05:00.000Z",
    },
    {
      id: "drv-10",
      name: "Sample archive.zip",
      kind: "Archive",
      updatedAt: "2026-11-01T19:30:00.000Z",
    },
  ],
};
