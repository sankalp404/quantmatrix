"""add job_run table and price_data composite index

Revision ID: 3e9ac1f
Revises: 0a1e2f3_widen_instrument_symbol
Create Date: 2025-11-23
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3e9ac1f"
down_revision = "1b2f_add_credentials_metadata"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Create job_run table only if missing (avoid transactional DDL aborts).
    if not insp.has_table("job_run"):
        op.create_table(
            "job_run",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("task_name", sa.String(length=100), nullable=False),
            sa.Column("params", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("counters", sa.JSON(), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column(
                "started_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
        )

    # Create indexes idempotently (Postgres supports IF NOT EXISTS).
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_jobrun_task_time ON job_run (task_name, started_at);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_jobrun_status_time ON job_run (status, started_at);"
    )

    # Add composite index for price_data if present (idempotent).
    if insp.has_table("price_data"):
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_symbol_interval_date ON price_data (symbol, interval, date);"
        )


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


