"""Drop obsolete hub_workspace table."""

import sqlalchemy as sa
from alembic import context, op

revision = "20261111_03"
down_revision = "20261109_02"
branch_labels = None
depends_on = None


def upgrade():
    if context.is_offline_mode():
        op.drop_table("hub_workspace")
        return
    if sa.inspect(op.get_bind()).has_table("hub_workspace"):
        op.drop_table("hub_workspace")


def downgrade():
    op.create_table(
        "hub_workspace",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("data_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
