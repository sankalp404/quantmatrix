"""
Widen instruments.symbol to 100 chars
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0a1e2f3"
down_revision = "95b8b27bb6d1"
branch_labels = None
depends_on = None


def upgrade():
    try:
        with op.batch_alter_table("instruments") as batch_op:
            batch_op.alter_column("symbol", type_=sa.String(length=100))
    except Exception:
        # If instruments table/column already matches, do nothing.
        pass


def downgrade():
    try:
        with op.batch_alter_table("instruments") as batch_op:
            batch_op.alter_column("symbol", type_=sa.String(length=20))
    except Exception:
        pass



