"""MarketSnapshotHistory: backfill wide columns from analysis_payload.

Revision ID: 4f2c9d0f5b22
Revises: 4f2c9d0f5b21
Create Date: 2026-01-12
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4f2c9d0f5b22"
down_revision = "4f2c9d0f5b21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_cols = {c["name"] for c in insp.get_columns("market_snapshot_history")}
    if "analysis_payload" not in existing_cols:
        # Already flipped in this environment.
        return

    # Backfill is best-effort and idempotent (only fills when column is NULL).
    # We assume PostgreSQL and that analysis_payload is stored as json/jsonb.
    #
    # Casting notes:
    # - float columns: NULLIF(text,'')::double precision
    # - int columns: NULLIF(text,'')::integer
    # - bool columns: NULLIF(text,'')::boolean
    # - strings: text directly
    # - timestamps: keep as text in payload; only next_earnings is a datetime column here,
    #   and is best-effort parsed by PostgreSQL.
    def jtxt(key: str) -> str:
        return f"(analysis_payload::jsonb ->> '{key}')"

    def f64(key: str) -> str:
        return f"NULLIF({jtxt(key)}, '')::double precision"

    def i32(key: str) -> str:
        return f"NULLIF({jtxt(key)}, '')::integer"

    def b01(key: str) -> str:
        return f"NULLIF({jtxt(key)}, '')::boolean"

    def strv(key: str) -> str:
        return f"NULLIF({jtxt(key)}, '')"

    updates = {
        # Fundamentals
        "name": strv("name"),
        "market_cap": f64("market_cap"),
        "sector": strv("sector"),
        "industry": strv("industry"),
        "sub_industry": strv("sub_industry"),

        # Indicators / MAs
        "sma_5": f64("sma_5"),
        "sma_14": f64("sma_14"),
        "sma_21": f64("sma_21"),
        "sma_100": f64("sma_100"),
        "sma_150": f64("sma_150"),
        "sma_200": f64("sma_200"),
        "ema_10": f64("ema_10"),
        "ema_8": f64("ema_8"),
        "ema_21": f64("ema_21"),
        "ema_200": f64("ema_200"),

        # ATRs / distances
        "atr_14": f64("atr_14"),
        "atr_30": f64("atr_30"),
        "atrp_14": f64("atrp_14"),
        "atrp_30": f64("atrp_30"),
        "atr_distance": f64("atr_distance"),
        "atr_percent": f64("atr_percent"),
        "atr_value": f64("atr_value"),

        # Range / ATR multiples
        "range_pos_20d": f64("range_pos_20d"),
        "range_pos_50d": f64("range_pos_50d"),
        "range_pos_52w": f64("range_pos_52w"),
        "atrx_sma_21": f64("atrx_sma_21"),
        "atrx_sma_50": f64("atrx_sma_50"),
        "atrx_sma_100": f64("atrx_sma_100"),
        "atrx_sma_150": f64("atrx_sma_150"),

        # Performance
        "perf_1d": f64("perf_1d"),
        "perf_3d": f64("perf_3d"),
        "perf_5d": f64("perf_5d"),
        "perf_20d": f64("perf_20d"),
        "perf_60d": f64("perf_60d"),
        "perf_120d": f64("perf_120d"),
        "perf_252d": f64("perf_252d"),
        "perf_mtd": f64("perf_mtd"),
        "perf_qtd": f64("perf_qtd"),
        "perf_ytd": f64("perf_ytd"),

        # Pine metrics
        "pct_dist_ema8": f64("pct_dist_ema8"),
        "pct_dist_ema21": f64("pct_dist_ema21"),
        "pct_dist_ema200": f64("pct_dist_ema200"),
        "atr_dist_ema8": f64("atr_dist_ema8"),
        "atr_dist_ema21": f64("atr_dist_ema21"),
        "atr_dist_ema200": f64("atr_dist_ema200"),
        "ma_bucket": strv("ma_bucket"),

        # TD / gaps / trends
        "td_buy_setup": i32("td_buy_setup"),
        "td_sell_setup": i32("td_sell_setup"),
        "td_buy_complete": b01("td_buy_complete"),
        "td_sell_complete": b01("td_sell_complete"),
        "td_buy_countdown": i32("td_buy_countdown"),
        "td_sell_countdown": i32("td_sell_countdown"),
        "td_perfect_buy": b01("td_perfect_buy"),
        "td_perfect_sell": b01("td_perfect_sell"),
        "gaps_unfilled_up": i32("gaps_unfilled_up"),
        "gaps_unfilled_down": i32("gaps_unfilled_down"),
        "trend_up_count": i32("trend_up_count"),
        "trend_down_count": i32("trend_down_count"),

        # Stage / RS
        "stage_label": strv("stage_label"),
        "stage_label_5d_ago": strv("stage_label_5d_ago"),
        "stage_slope_pct": f64("stage_slope_pct"),
        "stage_dist_pct": f64("stage_dist_pct"),
        "rs_mansfield_pct": f64("rs_mansfield_pct"),

        # Earnings
        "next_earnings": f"NULLIF({jtxt('next_earnings')}, '')::timestamp",
    }

    # Also fill headline columns if missing (these pre-exist, but keep them in sync).
    updates_headline = {
        "current_price": f64("current_price"),
        "rsi": f64("rsi"),
        "sma_50": f64("sma_50"),
        "macd": f64("macd"),
        "macd_signal": f64("macd_signal"),
        # atr_value already covered above (but exists pre-migration) – leave to wide mapping
    }

    # Single UPDATE for speed.
    sets = []
    for col, expr in {**updates_headline, **updates}.items():
        sets.append(f"{col} = COALESCE({col}, {expr})")

    sql = f"""
    UPDATE market_snapshot_history
    SET
      {", ".join(sets)}
    WHERE analysis_payload IS NOT NULL;
    """
    op.execute(sql)


def downgrade() -> None:
    # Irreversible data backfill; nothing to do.
    pass


