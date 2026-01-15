"""Drop MarketSnapshotHistory.analysis_payload after wide-column flip.

Revision ID: 4f2c9d0f5b23
Revises: 4f2c9d0f5b22
Create Date: 2026-01-12
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4f2c9d0f5b23"
down_revision = "4f2c9d0f5b22"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_cols = {c["name"] for c in insp.get_columns("market_snapshot_history")}
    if "analysis_payload" in existing_cols:
        op.drop_column("market_snapshot_history", "analysis_payload")


def downgrade() -> None:
    op.add_column("market_snapshot_history", sa.Column("analysis_payload", sa.JSON(), nullable=True))


