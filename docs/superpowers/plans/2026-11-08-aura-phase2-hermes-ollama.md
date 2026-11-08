# AURA Phase 2 Hermes + Local Ollama Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dual-path local inference — Hermes when compatible with local Ollama; otherwise the existing Ollama agent loop; remove OpenRouter defaults.

**Architecture:** Add a pure runtime-selection helper used by `container.build_app`. Hermes keeps its 64k gate for the Hermes path only. Status API reports `active_runtime`, `runtime_reason`, `hermes_installed`, `ollama_reachable`. Frontend status pills consume the new fields.

**Tech Stack:** Existing FastAPI/Python backend, React JSX frontend, pytest, Playwright (system Chrome).

## Global Constraints

- Hermes is the only agent framework; no LangChain/etc.
- Local Ollama only; do not call OpenRouter.
- Keep Hermes ≥64k requirement for Hermes path; fall back otherwise.
- No local worker / job queue (Phase 3).
- Do not install new browsers or tools.

---

### Task 1: Runtime selection helper + container wiring

**Files:**
- Create: `backend/src/personal_agent/infrastructure/model_providers/runtime_selection.py`
- Modify: `backend/src/personal_agent/app/container.py`
- Modify: `backend/src/personal_agent/infrastructure/model_providers/hermes_agent.py` (ensure defaults already use Ollama; keep 64k gate)
- Create: `backend/tests/unit/test_runtime_selection.py`

- [ ] **Step 1: Implement `select_inference_runtime(settings) -> RuntimeChoice`** with fields `active_runtime`, `reason`, `use_hermes`.
- [ ] **Step 2: Wire `build_app` to honor selection; store choice on container.**
- [ ] **Step 3: Unit tests for fake/ollama/hermes compatible/incompatible/cloud URL.**
- [ ] **Step 4: Commit**

---

### Task 2: Status/health + Ollama probe

**Files:**
- Modify: `backend/src/personal_agent/presentation/web/app.py`
- Modify: `backend/src/personal_agent/app/container.py` (AppContainer fields if needed)
- Modify: `backend/tests/integration/test_dashboard.py` as needed

- [ ] **Step 1: Add `ollama_reachable` probe helper (short timeout).**
- [ ] **Step 2: Extend `/api/status` and `/api/health`.**
- [ ] **Step 3: Tests assert new keys present.**
- [ ] **Step 4: Commit**

---

### Task 3: Frontend status display

**Files:**
- Modify: `frontend/src/app/layouts/DashboardLayout.jsx`
- Modify: `frontend/src/features/home/pages/HomePage.jsx`

- [ ] **Step 1: Show `active_runtime` and short `runtime_reason`.**
- [ ] **Step 2: Format + build.**
- [ ] **Step 3: Commit**

---

### Task 4: Config/docs cleanup

**Files:**
- Modify: `backend/.env.example`
- Modify: `render.yaml`
- Modify: `docs/hermes.md`, `docs/deploy.md`, `docs/architecture.md`

- [ ] **Step 1: Remove OpenRouter defaults; document dual-path.**
- [ ] **Step 2: Commit**

---

### Task 5: Verify

- [ ] **Step 1:** `cd backend && python -m pytest` (venv)
- [ ] **Step 2:** Frontend format/build; e2e with system Chrome + BACKEND_PYTHON
- [ ] **Step 3:** Final commit if needed
