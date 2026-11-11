# Phase 0 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Honest AURA foundation — naming, remove Hub/social mocks, TSK-02 transitions, Cursor rules, docs match code, Vitest/Playwright/mypy/import-linter in CI.

**Architecture:** Domain task_rules updated first; Hub/social surfaces deleted; docs + capabilities-driven status check; CI extended without weakening deploy.

**Tech Stack:** FastAPI/SQLAlchemy/Alembic, Next.js 15, Vitest, Playwright, import-linter, mypy, GitHub Actions

## Global Constraints

- Spec: `docs/superpowers/specs/2026-11-11-aura-phase0-foundation-design.md`
- Proposal: `docs/AURA_PROPOSAL.md` (create from Product Proposal file)
- No LinkedIn/Facebook/Hub in normal mode; no new mock surfaces
- TSK-02 matrix exactly as design
- Do not implement P1–P8 features in this plan
- Offline tests only; never commit secrets
- Conventional commits; CI must stay green

---

### Task 1: Cursor rules + AGENTS.md + AURA_PROPOSAL.md

**Files:**
- Create: `.cursor/rules/aura-core.mdc`, `.cursor/rules/aura-frontend.mdc`, `AGENTS.md`
- Create: `docs/AURA_PROPOSAL.md` (copy of `docs/AURA Personal AI Agent — Product Proposal and Functional Requirements.md`)
- Also commit the original proposal filename if still untracked

- [ ] **Step 1:** Copy proposal content to `docs/AURA_PROPOSAL.md` (identical bytes/content to the Product Proposal markdown).
- [ ] **Step 2:** Create rule files and `AGENTS.md` **verbatim** from proposal Part 3 §18 (aura-core, aura-frontend, AGENTS.md).
- [ ] **Step 3:** Commit

```bash
git add .cursor/rules AGENTS.md docs/AURA_PROPOSAL.md "docs/AURA Personal AI Agent — Product Proposal and Functional Requirements.md"
git commit -m "$(cat <<'EOF'
chore: add AURA Cursor rules, AGENTS.md, and proposal pointer

EOF
)"
```

---

### Task 2: TSK-02 task transition matrix

**Files:**
- Modify: `backend/src/personal_agent/domain/task_rules.py`
- Modify: `backend/tests/unit/test_task_service.py` (and add `test_task_rules_matrix.py` if clearer)
- Update frontend Tasks status dropdown if it still omits legal moves

- [ ] **Step 1: Failing tests for new legal moves**

```python
# backend/tests/unit/test_task_rules_matrix.py
import pytest
from personal_agent.domain.models import TaskStatus
from personal_agent.domain.task_rules import can_transition, transition, new_task, IllegalTaskTransitionError

ALLOWED = {
    TaskStatus.PLANNED: {TaskStatus.IN_PROGRESS, TaskStatus.DONE, TaskStatus.CANCELLED},
    TaskStatus.IN_PROGRESS: {TaskStatus.PLANNED, TaskStatus.BLOCKED, TaskStatus.DONE, TaskStatus.CANCELLED},
    TaskStatus.BLOCKED: {TaskStatus.PLANNED, TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
    TaskStatus.DONE: {TaskStatus.PLANNED},
    TaskStatus.CANCELLED: {TaskStatus.PLANNED},
}

@pytest.mark.parametrize("current", list(TaskStatus))
@pytest.mark.parametrize("proposed", list(TaskStatus))
def test_every_pair(current, proposed):
    expected = proposed == current or proposed in ALLOWED[current]
    assert can_transition(current, proposed) is (proposed in ALLOWED[current] or False)
    # can_transition does not treat no-op; transition() does
    if proposed == current:
        t = new_task("u", "t")
        t.status = current
        assert transition(t, proposed).status is current
        return
    t = new_task("u", "t")
    t.status = current
    if expected:
        assert transition(t, proposed).status is proposed
    else:
        with pytest.raises(IllegalTaskTransitionError):
            transition(t, proposed)
```

Fix the assert carefully: `can_transition` returns False for no-op same status (only `transition` allows no-op). So:

```python
def test_every_pair(current, proposed):
    t = new_task("u", "t")
    t.status = current
    if proposed == current:
        assert transition(t, proposed).status is current
        return
    legal = proposed in ALLOWED[current]
    assert can_transition(current, proposed) is legal
    if legal:
        assert transition(t, proposed).status is proposed
    else:
        with pytest.raises(IllegalTaskTransitionError):
            transition(t, proposed)
```

- [ ] **Step 2:** Run pytest — expect FAIL on planned→done.

```bash
cd backend && python -m pytest tests/unit/test_task_rules_matrix.py -v
```

- [ ] **Step 3:** Update `_ALLOWED` in `task_rules.py` to the design matrix. Fix `test_illegal_transition_is_rejected` in `test_task_service.py` (planned→done is now legal; pick another illegal e.g. done→cancelled).

- [ ] **Step 4:** Frontend Tasks status options: ensure Done is offered from planned and Reopen (planned) from done/cancelled where the UI advances status.

- [ ] **Step 5:** `pytest tests/unit/test_task_rules_matrix.py tests/unit/test_task_service.py -v` PASS → commit

```bash
git commit -m "$(cat <<'EOF'
fix(tasks): allow planned→done and reopen per TSK-02

EOF
)"
```

---

### Task 3: Remove Hub backend

**Files:**
- Modify: `app.py` (remove hub routes + HubStateRequest if any)
- Modify: `container.py` (drop hub)
- Delete or slim: `hub_store.py` — **keep** `GoogleConnectionStore` if it lives in the same file; split file if needed
- Delete: `tests/unit/test_hub_store.py` hub tests only; keep GoogleConnectionStore tests
- Create Alembic migration dropping `hub_workspace` if present
- Remove hub references from fake_provider copy

- [ ] Split `GoogleConnectionStore` into `google_connection_store.py` if still coupled to HubStore.
- [ ] Remove routes/tests/container field.
- [ ] Migration `drop_hub_workspace`.
- [ ] pytest green → commit `chore: remove HubStore and /api/hub/state`

---

### Task 4: Remove LinkedIn/Facebook from frontend

**Files:**
- Delete pages under `connections/linkedin`, `connections/facebook`
- Modify: nav (find `components/shell` or nav config), `channel-grid.tsx`, `health-strip.tsx`, `overview-page.tsx`, `capabilities.ts`, mocks
- Remove social-only mock notifications

- [ ] Grep for `linkedin|facebook` under `frontend/` and remove all live references.
- [ ] `npx tsc --noEmit` + `npm run format:check` → commit `chore(ui): remove LinkedIn and Facebook mock channels`

---

### Task 5: Docs honesty + feature-status check (FND-01, FND-02, FND-05)

**Files:**
- Rewrite: `README.md`, `docs/architecture.md`, `docs/deploy.md`, `frontend/README.md`
- Delete: `docs/references/product-mgt.md`
- Create: `docs/adr/0001-remove-hub-and-social-mocks.md`
- Create: `scripts/check-feature-status.mjs` (or `backend/scripts/...`) + `docs/feature-status.md` generated or checked against `capabilities.ts`
- Wire script into CI frontend or a small `docs` job

- [ ] Scrub “Agent Hub”, Product-Mgt, Vite-as-production-UI, “Google not implemented”.
- [ ] ADR records Hub/social removal.
- [ ] Commit `docs: align README/architecture with AURA Phase 0`

---

### Task 6: Vitest + Playwright smoke + CI (FND-04)

**Files:**
- `frontend/package.json` — add vitest, playwright (devDeps), scripts `test`, `test:e2e`
- `frontend/vitest.config.ts`, move or keep `agent-state.test.ts` under vitest
- `frontend/e2e/smoke.spec.ts` — register/login/chat/task/approve against fake backend **or** document skip if API not available: prefer spinning backend with fake provider in CI service, or mark e2e as `workflow` job that starts both

**Pragmatic CI acceptance for Phase 0:**

1. Vitest runs on every PR (`npm test`)
2. Playwright smoke runs if we can boot API with fake provider in the job; if too heavy, add job that starts `uvicorn` with test env + `next start` after build — implement the lighter path that still hits the acceptance flow

Minimum smoke if full stack is hard in one task:

- Playwright hits login page + authenticated shell with mocked API via `page.route` — only if proposal’s “fake provider” chat cannot run; prefer real fake provider.

- [ ] Implement Vitest for `agent-state.ts` (convert from node:test if needed).
- [ ] Implement Playwright smoke.
- [ ] Update `.github/workflows/ci.yml` frontend job: `npm test`; add e2e job or step.
- [ ] Commit `test: add Vitest and Playwright smoke for Phase 0`

---

### Task 7: mypy + import-linter (FND-07)

**Files:**
- `backend/pyproject.toml` — mypy + importlinter deps in `[project.optional-dependencies] dev`
- `.importlinter` or pyproject contracts: domain ↛ infrastructure/application/presentation
- CI backend job: `mypy src/personal_agent/domain src/personal_agent/application` and `lint-imports`

- [ ] Fix any real layer violations found (do not weaken contracts).
- [ ] Commit `chore(ci): enforce mypy and import-linter on domain/application`

---

### Task 8: Verify + mark spec implemented

- [ ] Full backend pytest + ruff; frontend format, tsc, test, build
- [ ] Grep: no Product-Mgt, Agent Hub, `/connections/linkedin` in app code
- [ ] Set Phase 0 spec status to Implemented; commit
- [ ] Do not push unless controller requests deploy

---

## Spec coverage

| Spec item | Task |
| --- | --- |
| FND-06 rules/AGENTS/proposal | 1 |
| TSK-02 | 2 |
| FND-03 Hub | 3 |
| FND-03 social mocks | 4 |
| FND-01/02/05 docs+ADR+status | 5 |
| FND-04 tests | 6 |
| FND-07 lint | 7 |
| Success criteria | 8 |
