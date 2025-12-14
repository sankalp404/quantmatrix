"""add job_run table and price_data composite index

Revision ID: 3e9ac1f
Revises: 0a1e2f3_widen_instrument_symbol
Create Date: 2025-11-23
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3e9ac1f"
down_revision = "0a1e2f3"
branch_labels = None
depends_on = None


def upgrade():
    # Create job_run table
    op.create_table(
        "job_run",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("task_name", sa.String(length=100), nullable=False),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("counters", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("idx_jobrun_task_time", "job_run", ["task_name", "started_at"], unique=False)
    op.create_index("idx_jobrun_status_time", "job_run", ["status", "started_at"], unique=False)

    # Add composite index for price_data if not present
    # Safe create: some databases support IF NOT EXISTS; Alembic/SA doesn't universally.
    # We attempt create and ignore if it exists.
    try:
        op.create_index("idx_symbol_interval_date", "price_data", ["symbol", "interval", "date"], unique=False)
    except Exception:
        pass


def downgrade():
    # Drop composite index for price_data
    try:
        op.drop_index("idx_symbol_interval_date", table_name="price_data")
    except Exception:
        pass
    # Drop job_run indexes and table
    try:
        op.drop_index("idx_jobrun_status_time", table_name="job_run")
    except Exception:
        pass
    try:
        op.drop_index("idx_jobrun_task_time", table_name="job_run")
    except Exception:
        pass
    op.drop_table("job_run")


