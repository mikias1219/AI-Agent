# AURA Phase 1 / P3 — Durable Approvals

**Date:** 2026-11-11  
**Status:** Approved — implementing (full-roadmap sequential)  
**Source:** `docs/AURA_PROPOSAL.md` Part 3 **P3** (APR-01..06; BR-02..05)

## Goal

Replace in-process approval waits with persisted approvals and pause/resume so COMMIT actions survive API restart; approve once; Chat/Today can share one ApprovalCard.

## Scope

- Persisted approval records (hash, expiry 24h, statuses)
- Run → awaiting_approval; resume after decision; idempotent execute
- destructive access kind (may already exist from P1)
- Edit-then-approve creates new hash; untrusted-content warning flag
- API decision endpoint; UI ApprovalCard
- Tests: restart, double-approve, expired, edit, group cannot decide

## Out of scope

Memory (P4), Today shell (P5), scheduler (P6).
