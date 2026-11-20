# ADR-0026: Six-destination shell

## Status

Accepted (supersedes the lean nine-item shell in `6274637` and proposal §41 navigation layout)

## Context

Owners chose IA v4: Today, Chat, Needs you, Plan, Agent, Settings. Mail that needs a reply belongs
in Needs you; a read-only list stays one click away. Existing URLs must keep working.

## Decision

- Primary nav: Today `/`, Chat `/chat`, Needs you `/inbox` (also `/mail`), Plan `/tasks` (also
  `/goals`, `/calendar`), Agent `/memory` (also `/routines`, `/activity`, `/connections`), Settings
  `/settings` in the footer.
- Hubs show one tab row; the shell header is the only page title.
- Mobile: bottom bar with Today, Chat, Needs you, Plan, More (opens the sidebar).
- Help stays at `/help` and is titled Help; the profile menu links to it.
- Design tokens and primitives (`PageFrame`, accessible `Tabs`, `Select`, `Banner`, `Skeleton`,
  focus-trapped `Drawer`/`Modal`, mounted `Toast`) land with this shell.

## Consequences

Work / Schedule hub labels are gone. Connections live under Agent. Overview and Skills tabs arrive
in a later phase. Playwright and unit nav expectations must follow the new labels.
