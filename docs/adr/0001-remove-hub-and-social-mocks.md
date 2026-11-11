# ADR 0001: Remove the Agent Hub store and social-channel mocks

- Status: Accepted
- Date: 2026-11-11

## Context

An earlier iteration added a "Personal Agent Hub": a `hub_workspace` table, a
`HubStore`, and `GET /api/hub/state`, plus LinkedIn and Facebook channel cards with
preview/mock behaviour, modelled on an external reference product. None of this was
backed by working integrations. Documentation also described the dashboard as a Vite
app served by the backend and said Google was not implemented, while production ran
Next.js on Vercel with working Google OAuth. The mismatch made the product look more
(and differently) complete than it was.

## Decision

- Remove `HubStore`, `/api/hub/state`, and the `hub_workspace` table (migration
  `20261111_03_drop_hub_workspace`).
- Remove the LinkedIn and Facebook mock channels from the UI. They return only when a
  real integration exists.
- Delete the Product-Mgt reference note; AURA's scope is defined by
  `docs/AURA_PROPOSAL.md`.
- Rewrite README, architecture, deploy, and frontend docs to describe what exists:
  Next.js, Google, Telegram, and the AURA shell.
- Track feature honesty mechanically: `frontend/lib/capabilities.ts` is the source,
  `docs/feature-status.md` is generated from it, and `scripts/check-feature-status.mjs`
  runs in CI and fails if a `mock` capability is advertised as Available or the file
  drifts.

## Consequences

- Docs and UI list only live features; unbuilt modules are labelled planned.
- Adding or flipping a capability requires regenerating `docs/feature-status.md`.
- Re-introducing a social channel needs a real integration (and its own ADR), not a
  preview card.
- The earlier `hub_workspace` migration stays in history; the drop migration is
  idempotent.
