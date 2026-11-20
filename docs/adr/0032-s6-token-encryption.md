# ADR-0032: S6 — AES-256-GCM for Google tokens at rest

Status: Accepted

## Context

`docs/TRANSFORMATION.md` S6 flagged the hand-built XOR+HMAC seal for Google OAuth tokens
as medium severity. Phase 5 deferred it; Phase 6 closes it.

## Decision

1. New seals use AES-256-GCM with a 12-byte nonce, key =
   `SHA-256("google-oauth-v2:" + DASHBOARD_SECRET_KEY)`, stored as `v2gcm:` +
   urlsafe-base64(nonce ‖ ciphertext‖tag).
2. Legacy v1 blobs (XOR + HMAC under `google-oauth-v1`) remain readable.
3. `GoogleConnectionStore.load_tokens` reseals v1 → v2 on read when either token needs
   migration, then commits.

## Consequences

- Dependency: `cryptography>=42`.
- Existing connections keep working without a bulk migration job.
- Rotating `DASHBOARD_SECRET_KEY` still invalidates sealed tokens (reconnect Google).
