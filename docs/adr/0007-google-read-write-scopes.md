# ADR 0007 — Google read/write scopes and Read-only switch

## Status

Accepted

## Context

P7 needs minimum Google scopes (INT-GOO-01) and a Connections Read-only switch that blocks every write tool while still allowing search/read. External email must be sanitized and labeled untrusted (BR-04).

## Decision

- Split OAuth into `GOOGLE_READ_SCOPES` and `GOOGLE_WRITE_SCOPES`; connect defaults to read-only consent (`state=ro=1`).
- Persist `google_connections.read_only` (default on). Leaving Read-only triggers re-consent for write scopes.
- `GoogleApiClient` refuses write methods when `read_only_provider()` is true.
- Gmail read/search wrap payloads with an untrusted notice and truncate bodies; ToolRegistry `untrusted_output` flags the run for later approvals.

## Consequences

- Owners can use Gmail/Calendar reads without granting send/event-write until they opt in.
- Injection text in email cannot by itself send mail; execute tools still require approval.
