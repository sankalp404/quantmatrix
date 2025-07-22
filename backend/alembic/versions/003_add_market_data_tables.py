"""add market data tables

Revision ID: 003
Revises: 002
Create Date: 2025-01-19 01:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

def upgrade():
    # StockInfo table
    op.create_table('stock_info',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=True),
        sa.Column('sector', sa.String(length=100), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('market_cap', sa.Float(), nullable=True),
        sa.Column('pe_ratio', sa.Float(), nullable=True),
        sa.Column('dividend_yield', sa.Float(), nullable=True),
        sa.Column('beta', sa.Float(), nullable=True),
        sa.Column('revenue_growth', sa.Float(), nullable=True),
        sa.Column('profit_margin', sa.Float(), nullable=True),
        sa.Column('exchange', sa.String(length=20), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=True),
        sa.Column('country', sa.String(length=50), nullable=True),
        sa.Column('data_source', sa.String(length=50), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sector_market_cap', 'stock_info', ['sector', 'market_cap'], unique=False)
    op.create_index('idx_last_updated', 'stock_info', ['last_updated'], unique=False)
    op.create_index(op.f('ix_stock_info_id'), 'stock_info', ['id'], unique=False)
    op.create_index(op.f('ix_stock_info_sector'), 'stock_info', ['sector'], unique=False)
    op.create_index(op.f('ix_stock_info_symbol'), 'stock_info', ['symbol'], unique=True)

    # PriceData table
    op.create_table('price_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('open_price', sa.Float(), nullable=False),
        sa.Column('high_price', sa.Float(), nullable=False),
        sa.Column('low_price', sa.Float(), nullable=False),
        sa.Column('close_price', sa.Float(), nullable=False),
        sa.Column('adjusted_close', sa.Float(), nullable=True),
        sa.Column('volume', sa.Integer(), nullable=True),
        sa.Column('true_range', sa.Float(), nullable=True),
        sa.Column('data_source', sa.String(length=50), nullable=True),
        sa.Column('interval', sa.String(length=10), nullable=True),
        sa.Column('is_adjusted', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol', 'date', 'interval', name='uq_symbol_date_interval')
    )
    op.create_index('idx_date_range', 'price_data', ['date'], unique=False)
    op.create_index('idx_symbol_date', 'price_data', ['symbol', 'date'], unique=False)
    op.create_index(op.f('ix_price_data_date'), 'price_data', ['date'], unique=False)
    op.create_index(op.f('ix_price_data_id'), 'price_data', ['id'], unique=False)
    op.create_index(op.f('ix_price_data_symbol'), 'price_data', ['symbol'], unique=False)

    # ATRData table
    op.create_table('atr_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('calculation_date', sa.DateTime(), nullable=False),
        sa.Column('period', sa.Integer(), nullable=True),
        sa.Column('current_atr', sa.Float(), nullable=False),
        sa.Column('atr_percentage', sa.Float(), nullable=False),
        sa.Column('volatility_rating', sa.String(length=20), nullable=True),
        sa.Column('volatility_trend', sa.String(length=20), nullable=True),
        sa.Column('current_price', sa.Float(), nullable=True),
        sa.Column('data_points_used', sa.Integer(), nullable=True),
        sa.Column('calculation_confidence', sa.Float(), nullable=True),
        sa.Column('data_source', sa.String(length=50), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol', 'calculation_date', 'period', name='uq_symbol_date_period')
    )
    op.create_index('idx_symbol_updated', 'atr_data', ['symbol', 'last_updated'], unique=False)
    op.create_index('idx_volatility_rating', 'atr_data', ['volatility_rating'], unique=False)
    op.create_index(op.f('ix_atr_data_calculation_date'), 'atr_data', ['calculation_date'], unique=False)
    op.create_index(op.f('ix_atr_data_id'), 'atr_data', ['id'], unique=False)
    op.create_index(op.f('ix_atr_data_symbol'), 'atr_data', ['symbol'], unique=False)

    # SectorMetrics table
    op.create_table('sector_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sector', sa.String(length=100), nullable=False),
        sa.Column('avg_atr_percentage', sa.Float(), nullable=True),
        sa.Column('median_atr_percentage', sa.Float(), nullable=True),
        sa.Column('volatility_percentile_90', sa.Float(), nullable=True),
        sa.Column('volatility_percentile_10', sa.Float(), nullable=True),
        sa.Column('is_growth_oriented', sa.Boolean(), nullable=True),
        sa.Column('avg_revenue_growth', sa.Float(), nullable=True),
        sa.Column('avg_pe_ratio', sa.Float(), nullable=True),
        sa.Column('dca_buy_threshold', sa.Float(), nullable=True),
        sa.Column('dca_sell_threshold', sa.Float(), nullable=True),
        sa.Column('sample_size', sa.Integer(), nullable=True),
        sa.Column('last_calculated', sa.DateTime(), nullable=True),
        sa.Column('calculation_period_days', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_growth_oriented', 'sector_metrics', ['is_growth_oriented'], unique=False)
    op.create_index('idx_last_calculated', 'sector_metrics', ['last_calculated'], unique=False)
    op.create_index(op.f('ix_sector_metrics_id'), 'sector_metrics', ['id'], unique=False)
    op.create_index(op.f('ix_sector_metrics_sector'), 'sector_metrics', ['sector'], unique=True)

    # MarketDataSync table
    op.create_table('market_data_sync',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sync_type', sa.String(length=50), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('records_processed', sa.Integer(), nullable=True),
        sa.Column('records_updated', sa.Integer(), nullable=True),
        sa.Column('records_created', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('data_source', sa.String(length=50), nullable=True),
        sa.Column('sync_config', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_started_at', 'market_data_sync', ['started_at'], unique=False)
    op.create_index('idx_sync_type_status', 'market_data_sync', ['sync_type', 'status'], unique=False)
    op.create_index(op.f('ix_market_data_sync_id'), 'market_data_sync', ['id'], unique=False)
    op.create_index(op.f('ix_market_data_sync_symbol'), 'market_data_sync', ['symbol'], unique=False)

    # DataQuality table
    op.create_table('data_quality',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('table_name', sa.String(length=100), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=True),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('threshold_min', sa.Float(), nullable=True),
        sa.Column('threshold_max', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('measured_at', sa.DateTime(), nullable=True),
        sa.Column('measurement_period', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_status_measured', 'data_quality', ['status', 'measured_at'], unique=False)
    op.create_index('idx_table_metric', 'data_quality', ['table_name', 'metric_name'], unique=False)
    op.create_index(op.f('ix_data_quality_id'), 'data_quality', ['id'], unique=False)
    op.create_index(op.f('ix_data_quality_measured_at'), 'data_quality', ['measured_at'], unique=False)
    op.create_index(op.f('ix_data_quality_symbol'), 'data_quality', ['symbol'], unique=False)

def downgrade():
    # Drop tables in reverse order
    op.drop_table('data_quality')
    op.drop_table('market_data_sync')
    op.drop_table('sector_metrics')
    op.drop_table('atr_data')
    op.drop_table('price_data')
    op.drop_table('stock_info') 