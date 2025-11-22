"""
Add credentials metadata columns
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "1b2f_add_credentials_metadata"
down_revision = "0a1e2f3"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("account_credentials") as batch_op:
        batch_op.add_column(sa.Column("provider", sa.Enum("ibkr", "tastytrade", "schwab", "fidelity", "robinhood", "unknown_broker", name="brokertype"), nullable=True))
        batch_op.add_column(sa.Column("credential_type", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("username_hint", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("last_refreshed_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("refresh_token_expires_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("last_error", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("rotation_count", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("account_credentials") as batch_op:
        batch_op.drop_column("rotation_count")
        batch_op.drop_column("last_error")
        batch_op.drop_column("refresh_token_expires_at")
        batch_op.drop_column("last_refreshed_at")
        batch_op.drop_column("username_hint")
        batch_op.drop_column("credential_type")
        batch_op.drop_column("provider")




