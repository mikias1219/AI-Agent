# Personal agent dashboard — original design proposal

## Implementation status

The initial design below is retained as design history. The React UI now uses real
backend authentication, chat/history, tasks/approvals, activity, and Telegram management.
The duplicate Python static UI has been retired. Telegram is the first implemented
external app. Social content generation/publishing remains deferred and is shown as
planned, without example-generation or simulated-publishing behavior in the active UI.
See `backend/README.md` and `frontend/README.md` for current commands and capabilities.

## Product direction

One personal agent, one workspace. Telegram, Google Workspace, LinkedIn, and Facebook
are connections used by that agent. The interface should not make the owner manage a
separate agent for every app.

This is a design-first proposal. The existing Python dashboard and Telegram runner
remain intact. The interactive prototype is in `frontend/`.
The prototype now uses React, Vite, and Tailwind CSS. Run `npm install` then
`npm run dev` from `frontend` to preview it. See the prototype README
for login, registration, and dashboard routes.

## Navigation and hierarchy

| Area | Primary purpose |
| --- | --- |
| Today | One request box, three shortcuts, a draft to resume, and a compact app summary |
| My agent | Main conversation; the same agent also answers through Telegram |
| Content studio | Brief, platform-specific drafts, editing, and final review |
| Connections | Each app’s scope, setup, and connection state |
| Activity | Outcomes, approvals, errors, and links back to the work |

Settings such as model choice, authentication, and tool permissions belong in a later
workspace/settings surface. They should not compete with everyday tasks on Today.
Tasks, calendar, and email should be introduced only when backed by working features;
avoid adding empty top-level sections for every future capability.

## Content workflow

1. Ask “Generate today’s post for LinkedIn and Facebook” from Today or the agent.
2. Confirm or edit the topic, tone, and target platforms in Content Studio.
3. Produce a separate draft for each platform. Switching tabs preserves edits.
4. Show the exact final text and destination together in a review dialog.
5. Once accounts and publishing are implemented, request explicit approval of those
   drafts and destinations, then show an independent outcome per platform.

A failed Facebook publish must not conceal a successful LinkedIn publish. The future
implementation should retain destination-level states and retry only failed targets.
Changes made after approval require a new review of the changed content. Scheduling,
media uploads, account selection, and analytics are deferred until the text workflow
works reliably. Real platform permissions and supported destination types must be
verified during integration implementation; the prototype does not establish support
for posting to any particular personal account type.

## Visual direction

A light neutral canvas, white surfaces, soft violet accents, rounded cards, compact typography,
and generous spacing. Persistent navigation has five destinations. The home page has
one main action, with supporting work below it. Technical diagnostics stay inside
connection details or settings. Platform identity is conveyed with small badges rather
than large competing brand colors. The layout collapses to one column on small screens.

## Prototype boundaries

The prototype is deliberately separate from the live dashboard. Login, registration,
and password reset screens are included as UI demos with field validation and password
visibility controls. No credentials are persisted or sent; registration does not create
a real account, and reset does not send email. It includes navigation,
a request box, a sample conversation, editable platform drafts, topic/tone-dependent
example generation, destination selection, final review, simulated publishing, and a
preview activity timeline. Example generation is a local template, not AI. Drafts and
activity exist only in browser memory and reset on reload. No accounts are linked, no
credentials are read, and no network requests or posts are made.

## Implementation sequence after design review

1. Apply the reviewed layout to the existing authenticated local dashboard, preserving
   its services, permissions, audit log, and existing routes.
2. Improve the shared agent’s instructions and Telegram reliability; verify live Ollama
   responses in the user’s environment.
3. Add durable content briefs and platform drafts, connected to the shared agent.
4. Add verified account connections and granular permissions one app at a time.
5. Wire final approval, per-platform publishing outcomes, and safe retries.

## Validation

Validation results for the React/Tailwind revision are recorded in `frontend/README.md`.
The production Python dashboard and its authentication remain unchanged.
