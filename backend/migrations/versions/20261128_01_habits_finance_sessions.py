"""Habits, finance ledger and revocable sessions (roadmap P0-5, P1-2, P1-3)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261128_01"
down_revision = "20261127_01"
branch_labels = None
depends_on = None

# Creation order respects foreign keys; drop runs in reverse.
_TABLES = (
    "user_sessions",
    "habits",
    "habit_checkins",
    "fin_accounts",
    "fin_categories",
    "fin_transactions",
    "fin_recurring_rules",
    "fin_occurrences",
    "fin_budgets",
    "fin_budget_lines",
    "fin_savings_goals",
    "fin_contributions",
)


def _tables() -> list[sa.Table]:
    from personal_agent.infrastructure.persistence.models import Base

    return [Base.metadata.tables[name] for name in _TABLES]


def upgrade() -> None:
    bind = op.get_bind()
    for table in _tables():
        table.create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(_tables()):
        table.drop(bind, checkfirst=True)
