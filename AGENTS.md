# AURA agent instructions
Read docs/AURA_PROPOSAL.md and .cursor/rules first.
Backend (from backend/): python -m pytest; ruff check .; ruff format --check .; mypy src/personal_agent/domain src/personal_agent/application
Frontend (from frontend/): npm run format:check; npx tsc --noEmit; npm run build; npm test; npm run test:e2e
Never commit secrets or .env files. Never bypass approvals.
