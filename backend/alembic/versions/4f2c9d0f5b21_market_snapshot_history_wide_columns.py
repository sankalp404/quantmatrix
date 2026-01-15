"""MarketSnapshotHistory: add wide columns (replace JSON payload).

Revision ID: 4f2c9d0f5b21
Revises: b6e2a756fdad
Create Date: 2026-01-12
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4f2c9d0f5b21"
down_revision = "b6e2a756fdad"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_cols = {c["name"] for c in insp.get_columns("market_snapshot_history")}

    # NOTE: We intentionally keep existing headline columns (current_price, rsi, etc.)
    # and add the remaining snapshot fields as nullable columns.
    #
    # We will backfill these columns from analysis_payload in the next migration,
    # then drop analysis_payload in a follow-up migration once writers/readers flip.
    def add(col: sa.Column) -> None:
        if col.name not in existing_cols:
            op.add_column("market_snapshot_history", col)
            existing_cols.add(col.name)

    add(sa.Column("name", sa.String(length=200), nullable=True))
    add(sa.Column("market_cap", sa.Float(), nullable=True))
    add(sa.Column("sector", sa.String(length=100), nullable=True))
    add(sa.Column("industry", sa.String(length=100), nullable=True))
    add(sa.Column("sub_industry", sa.String(length=100), nullable=True))

    # Canonical consolidated MAs / ATRs
    add(sa.Column("sma_5", sa.Float(), nullable=True))
    add(sa.Column("sma_14", sa.Float(), nullable=True))
    add(sa.Column("sma_21", sa.Float(), nullable=True))
    add(sa.Column("sma_100", sa.Float(), nullable=True))
    add(sa.Column("sma_150", sa.Float(), nullable=True))
    add(sa.Column("sma_200", sa.Float(), nullable=True))
    add(sa.Column("ema_10", sa.Float(), nullable=True))
    add(sa.Column("ema_8", sa.Float(), nullable=True))
    add(sa.Column("ema_21", sa.Float(), nullable=True))
    add(sa.Column("ema_200", sa.Float(), nullable=True))

    # ATR windows
    add(sa.Column("atr_14", sa.Float(), nullable=True))
    add(sa.Column("atr_30", sa.Float(), nullable=True))
    add(sa.Column("atrp_14", sa.Float(), nullable=True))
    add(sa.Column("atrp_30", sa.Float(), nullable=True))
    add(sa.Column("atr_distance", sa.Float(), nullable=True))
    add(sa.Column("atr_percent", sa.Float(), nullable=True))
    add(sa.Column("atr_value", sa.Float(), nullable=True))  # keep parity

    # Range position + ATR multiples
    add(sa.Column("range_pos_20d", sa.Float(), nullable=True))
    add(sa.Column("range_pos_50d", sa.Float(), nullable=True))
    add(sa.Column("range_pos_52w", sa.Float(), nullable=True))
    add(sa.Column("atrx_sma_21", sa.Float(), nullable=True))
    add(sa.Column("atrx_sma_50", sa.Float(), nullable=True))
    add(sa.Column("atrx_sma_100", sa.Float(), nullable=True))
    add(sa.Column("atrx_sma_150", sa.Float(), nullable=True))

    # Performance windows
    add(sa.Column("perf_1d", sa.Float(), nullable=True))
    add(sa.Column("perf_3d", sa.Float(), nullable=True))
    add(sa.Column("perf_5d", sa.Float(), nullable=True))
    add(sa.Column("perf_20d", sa.Float(), nullable=True))
    add(sa.Column("perf_60d", sa.Float(), nullable=True))
    add(sa.Column("perf_120d", sa.Float(), nullable=True))
    add(sa.Column("perf_252d", sa.Float(), nullable=True))
    add(sa.Column("perf_mtd", sa.Float(), nullable=True))
    add(sa.Column("perf_qtd", sa.Float(), nullable=True))
    add(sa.Column("perf_ytd", sa.Float(), nullable=True))

    # Pine Script metrics
    add(sa.Column("pct_dist_ema8", sa.Float(), nullable=True))
    add(sa.Column("pct_dist_ema21", sa.Float(), nullable=True))
    add(sa.Column("pct_dist_ema200", sa.Float(), nullable=True))
    add(sa.Column("atr_dist_ema8", sa.Float(), nullable=True))
    add(sa.Column("atr_dist_ema21", sa.Float(), nullable=True))
    add(sa.Column("atr_dist_ema200", sa.Float(), nullable=True))
    add(sa.Column("ma_bucket", sa.String(length=16), nullable=True))

    # TD sequential + gaps + trends
    add(sa.Column("td_buy_setup", sa.Integer(), nullable=True))
    add(sa.Column("td_sell_setup", sa.Integer(), nullable=True))
    add(sa.Column("td_buy_complete", sa.Boolean(), nullable=True))
    add(sa.Column("td_sell_complete", sa.Boolean(), nullable=True))
    add(sa.Column("td_buy_countdown", sa.Integer(), nullable=True))
    add(sa.Column("td_sell_countdown", sa.Integer(), nullable=True))
    add(sa.Column("td_perfect_buy", sa.Boolean(), nullable=True))
    add(sa.Column("td_perfect_sell", sa.Boolean(), nullable=True))
    add(sa.Column("gaps_unfilled_up", sa.Integer(), nullable=True))
    add(sa.Column("gaps_unfilled_down", sa.Integer(), nullable=True))
    add(sa.Column("trend_up_count", sa.Integer(), nullable=True))
    add(sa.Column("trend_down_count", sa.Integer(), nullable=True))

    # Stage / RS
    add(sa.Column("stage_label", sa.String(length=10), nullable=True))
    add(sa.Column("stage_label_5d_ago", sa.String(length=10), nullable=True))
    add(sa.Column("stage_slope_pct", sa.Float(), nullable=True))
    add(sa.Column("stage_dist_pct", sa.Float(), nullable=True))
    add(sa.Column("rs_mansfield_pct", sa.Float(), nullable=True))

    # Corporate events
    add(sa.Column("next_earnings", sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Reverse order (safe for downgrade).
    op.drop_column("market_snapshot_history", "next_earnings")
    op.drop_column("market_snapshot_history", "rs_mansfield_pct")
    op.drop_column("market_snapshot_history", "stage_dist_pct")
    op.drop_column("market_snapshot_history", "stage_slope_pct")
    op.drop_column("market_snapshot_history", "stage_label_5d_ago")
    op.drop_column("market_snapshot_history", "stage_label")
    op.drop_column("market_snapshot_history", "trend_down_count")
    op.drop_column("market_snapshot_history", "trend_up_count")
    op.drop_column("market_snapshot_history", "gaps_unfilled_down")
    op.drop_column("market_snapshot_history", "gaps_unfilled_up")
    op.drop_column("market_snapshot_history", "td_perfect_sell")
    op.drop_column("market_snapshot_history", "td_perfect_buy")
    op.drop_column("market_snapshot_history", "td_sell_countdown")
    op.drop_column("market_snapshot_history", "td_buy_countdown")
    op.drop_column("market_snapshot_history", "td_sell_complete")
    op.drop_column("market_snapshot_history", "td_buy_complete")
    op.drop_column("market_snapshot_history", "td_sell_setup")
    op.drop_column("market_snapshot_history", "td_buy_setup")
    op.drop_column("market_snapshot_history", "ma_bucket")
    op.drop_column("market_snapshot_history", "atr_dist_ema200")
    op.drop_column("market_snapshot_history", "atr_dist_ema21")
    op.drop_column("market_snapshot_history", "atr_dist_ema8")
    op.drop_column("market_snapshot_history", "pct_dist_ema200")
    op.drop_column("market_snapshot_history", "pct_dist_ema21")
    op.drop_column("market_snapshot_history", "pct_dist_ema8")
    op.drop_column("market_snapshot_history", "perf_ytd")
    op.drop_column("market_snapshot_history", "perf_qtd")
    op.drop_column("market_snapshot_history", "perf_mtd")
    op.drop_column("market_snapshot_history", "perf_252d")
    op.drop_column("market_snapshot_history", "perf_120d")
    op.drop_column("market_snapshot_history", "perf_60d")
    op.drop_column("market_snapshot_history", "perf_20d")
    op.drop_column("market_snapshot_history", "perf_5d")
    op.drop_column("market_snapshot_history", "perf_3d")
    op.drop_column("market_snapshot_history", "perf_1d")
    op.drop_column("market_snapshot_history", "atrx_sma_150")
    op.drop_column("market_snapshot_history", "atrx_sma_100")
    op.drop_column("market_snapshot_history", "atrx_sma_50")
    op.drop_column("market_snapshot_history", "atrx_sma_21")
    op.drop_column("market_snapshot_history", "range_pos_52w")
    op.drop_column("market_snapshot_history", "range_pos_50d")
    op.drop_column("market_snapshot_history", "range_pos_20d")
    op.drop_column("market_snapshot_history", "atr_value")
    op.drop_column("market_snapshot_history", "atr_percent")
    op.drop_column("market_snapshot_history", "atr_distance")
    op.drop_column("market_snapshot_history", "atrp_30")
    op.drop_column("market_snapshot_history", "atrp_14")
    op.drop_column("market_snapshot_history", "atr_30")
    op.drop_column("market_snapshot_history", "atr_14")
    op.drop_column("market_snapshot_history", "ema_200")
    op.drop_column("market_snapshot_history", "ema_21")
    op.drop_column("market_snapshot_history", "ema_8")
    op.drop_column("market_snapshot_history", "ema_10")
    op.drop_column("market_snapshot_history", "sma_200")
    op.drop_column("market_snapshot_history", "sma_150")
    op.drop_column("market_snapshot_history", "sma_100")
    op.drop_column("market_snapshot_history", "sma_21")
    op.drop_column("market_snapshot_history", "sma_14")
    op.drop_column("market_snapshot_history", "sma_5")
    op.drop_column("market_snapshot_history", "sub_industry")
    op.drop_column("market_snapshot_history", "industry")
    op.drop_column("market_snapshot_history", "sector")
    op.drop_column("market_snapshot_history", "market_cap")
    op.drop_column("market_snapshot_history", "name")


