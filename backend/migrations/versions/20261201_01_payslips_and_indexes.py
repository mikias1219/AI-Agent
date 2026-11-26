"""Payslips (salary components and deductions per pay period) and a composite ledger index."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261201_01"
down_revision = "20261130_01"
branch_labels = None
depends_on = None

_INDEX = "ix_fin_tx_owner_when"


def upgrade() -> None:
    from personal_agent.infrastructure.persistence.models import Base

    bind = op.get_bind()
    Base.metadata.tables["fin_payslips"].create(bind, checkfirst=True)
    existing = {i["name"] for i in sa.inspect(bind).get_indexes("fin_transactions")}
    if _INDEX not in existing:
        op.create_index(_INDEX, "fin_transactions", ["owner_user_id", "occurred_at"])


def downgrade() -> None:
    bind = op.get_bind()
    existing = {i["name"] for i in sa.inspect(bind).get_indexes("fin_transactions")}
    if _INDEX in existing:
        op.drop_index(_INDEX, table_name="fin_transactions")
    op.drop_table("fin_payslips")
