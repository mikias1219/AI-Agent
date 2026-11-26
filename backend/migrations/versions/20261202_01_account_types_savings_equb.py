"""Allow savings and Equb accounts (fin_accounts.type check constraint)."""

from __future__ import annotations

from alembic import op

revision = "20261202_01"
down_revision = "20261201_01"
branch_labels = None
depends_on = None

_NAME = "ck_fin_account_type"
_NEW = "type in ('cash','bank','mobile_money','card','savings','equb')"
_OLD = "type in ('cash','bank','mobile_money','card')"


def _swap(condition: str) -> None:
    # batch mode recreates the table on SQLite, which cannot alter constraints in place
    with op.batch_alter_table("fin_accounts") as batch:
        batch.drop_constraint(_NAME, type_="check")
        batch.create_check_constraint(_NAME, condition)


def upgrade() -> None:
    _swap(_NEW)


def downgrade() -> None:
    op.execute("UPDATE fin_accounts SET type = 'bank' WHERE type IN ('savings', 'equb')")
    _swap(_OLD)
