"""Add Personal Agent Hub workspace and Google connection tables."""

import sqlalchemy as sa
from alembic import context, op

revision = "20261109_02"
down_revision = "20261030_01"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if context.is_offline_mode() or not inspector.has_table("hub_workspace"):
        op.create_table(
            "hub_workspace",
            sa.Column("id", sa.String(32), primary_key=True),
            sa.Column("data_json", sa.Text(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True)),
        )
    if context.is_offline_mode() or not inspector.has_table("google_connections"):
        op.create_table(
            "google_connections",
            sa.Column("id", sa.String(32), primary_key=True),
            sa.Column("email", sa.String(254)),
            sa.Column("connected", sa.Integer()),
            sa.Column("access_token", sa.Text()),
            sa.Column("refresh_token", sa.Text()),
            sa.Column("scopes", sa.Text()),
            sa.Column("updated_at", sa.DateTime(timezone=True)),
        )


def downgrade():
    op.drop_table("google_connections")
    op.drop_table("hub_workspace")
