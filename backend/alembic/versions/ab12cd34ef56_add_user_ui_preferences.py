"""add user ui_preferences

Revision ID: ab12cd34ef56
Revises: 9b2a1a7a3a3f
Create Date: 2026-01-05
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ab12cd34ef56"
down_revision = "9b2a1a7a3a3f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = {c["name"] for c in insp.get_columns("users")}
    if "ui_preferences" not in existing:
        op.add_column("users", sa.Column("ui_preferences", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = {c["name"] for c in insp.get_columns("users")}
    if "ui_preferences" in existing:
        op.drop_column("users", "ui_preferences")


