"""Add the local workspace owner account without disturbing existing agent tables."""

import sqlalchemy as sa
from alembic import context, op

revision = "20261030_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    if context.is_offline_mode() or not sa.inspect(op.get_bind()).has_table("workspace_accounts"):
        op.create_table(
            "workspace_accounts",
            sa.Column("id", sa.String(16), primary_key=True),
            sa.Column("name", sa.String(80), nullable=False),
            sa.Column("email", sa.String(254), nullable=False),
            sa.Column("password_hash", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True)),
        )


def downgrade():
    op.drop_table("workspace_accounts")
