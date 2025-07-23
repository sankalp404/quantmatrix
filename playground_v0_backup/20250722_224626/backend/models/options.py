from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum, Index, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

from backend.models import Base

class OptionType(enum.Enum):
    CALL = "call"
    PUT = "put"

class OrderAction(enum.Enum):
    BUY_TO_OPEN = "buy_to_open"
    SELL_TO_OPEN = "sell_to_open"
    BUY_TO_CLOSE = "buy_to_close"
    SELL_TO_CLOSE = "sell_to_close"

class OrderStatus(enum.Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class StrategyType(enum.Enum):
    ATR_MATRIX = "atr_matrix"
    COVERED_CALL = "covered_call"
    CASH_SECURED_PUT = "cash_secured_put"
    IRON_CONDOR = "iron_condor"
    BUTTERFLY = "butterfly"
    STRADDLE = "straddle"
    STRANGLE = "strangle"
    CUSTOM = "custom"

class TastytradeAccount(Base):
    """Tastytrade account information for options trading."""
    __tablename__ = "tastytrade_accounts"
    
    id = Column(Integer, primary_key=True)
    account_number = Column(String(50), unique=True, nullable=False)
    nickname = Column(String(100))
    account_type = Column(String(50))  # Options Trading, etc.
    is_margin = Column(Boolean, default=False)
    day_trader_status = Column(Boolean, default=False)
    account_status = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships removed - using regular Account model for options now
    orders = relationship("OptionOrder", back_populates="account")
    strategies = relationship("TradingStrategy", back_populates="account")

class OptionInstrument(Base):
    """Options instrument details."""
    __tablename__ = "option_instruments"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(50), unique=True, nullable=False)  # Full option symbol
    underlying_symbol = Column(String(20), nullable=False)
    strike_price = Column(Numeric(12, 4), nullable=False)
    expiration_date = Column(DateTime, nullable=False)
    option_type = Column(Enum(OptionType), nullable=False)
    multiplier = Column(Integer, default=100)
    streamer_symbol = Column(String(100))  # For real-time data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    positions = relationship("OptionPosition", back_populates="option")
    orders = relationship("OptionOrder", back_populates="option")
    greeks = relationship("OptionGreeks", back_populates="option")
    prices = relationship("OptionPrice", back_populates="option")
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_option_underlying_expiration', 'underlying_symbol', 'expiration_date'),
        Index('ix_option_strike_type', 'strike_price', 'option_type'),
    )

class OptionPosition(Base):
    """Options positions for each account."""
    __tablename__ = "option_positions"
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)  # Changed to accounts table
    option_id = Column(Integer, ForeignKey("option_instruments.id"), nullable=False)
    quantity = Column(Integer, nullable=False)  # Can be negative for short positions
    average_open_price = Column(Numeric(12, 4), nullable=False)
    current_price = Column(Numeric(12, 4))
    market_value = Column(Numeric(12, 2))
    unrealized_pnl = Column(Numeric(12, 2))
    unrealized_pnl_pct = Column(Numeric(8, 4))
    day_pnl = Column(Numeric(12, 2))
    position_cost = Column(Numeric(12, 2))  # Total cost basis
    strategy_id = Column(Integer, ForeignKey("trading_strategies.id"))  # Link to strategy
    opened_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = relationship("Account", back_populates="option_positions")  # Changed to Account
    option = relationship("OptionInstrument", back_populates="positions")
    strategy = relationship("TradingStrategy", back_populates="positions")

class OptionGreeks(Base):
    """Real-time Greeks data for options."""
    __tablename__ = "option_greeks"
    
    id = Column(Integer, primary_key=True)
    option_id = Column(Integer, ForeignKey("option_instruments.id"), nullable=False)
    price = Column(Numeric(12, 4))
    implied_volatility = Column(Numeric(8, 6))
    delta = Column(Numeric(8, 6))
    gamma = Column(Numeric(10, 8))
    theta = Column(Numeric(8, 6))
    vega = Column(Numeric(8, 6))
    rho = Column(Numeric(8, 6))
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    option = relationship("OptionInstrument", back_populates="greeks")
    
    # Index for time-series queries
    __table_args__ = (
        Index('ix_greeks_option_timestamp', 'option_id', 'timestamp'),
    )

class OptionPrice(Base):
    """Real-time price data for options."""
    __tablename__ = "option_prices"
    
    id = Column(Integer, primary_key=True)
    option_id = Column(Integer, ForeignKey("option_instruments.id"), nullable=False)
    bid_price = Column(Numeric(12, 4))
    ask_price = Column(Numeric(12, 4))
    last_price = Column(Numeric(12, 4))
    bid_size = Column(Integer)
    ask_size = Column(Integer)
    volume = Column(Integer)
    open_interest = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    option = relationship("OptionInstrument", back_populates="prices")
    
    # Index for time-series queries
    __table_args__ = (
        Index('ix_prices_option_timestamp', 'option_id', 'timestamp'),
    )

class OptionOrder(Base):
    """Options orders and executions."""
    __tablename__ = "option_orders"
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("tastytrade_accounts.id"), nullable=False)
    option_id = Column(Integer, ForeignKey("option_instruments.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("trading_strategies.id"))  # Link to strategy
    external_order_id = Column(String(100))  # ID from Tastytrade
    action = Column(Enum(OrderAction), nullable=False)
    quantity = Column(Integer, nullable=False)
    order_type = Column(String(20))  # LIMIT, MARKET, etc.
    limit_price = Column(Numeric(12, 4))
    filled_price = Column(Numeric(12, 4))
    filled_quantity = Column(Integer, default=0)
    status = Column(Enum(OrderStatus), nullable=False)
    commission = Column(Numeric(8, 2))
    fees = Column(Numeric(8, 2))
    time_in_force = Column(String(20))  # DAY, GTC, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    filled_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    
    # Relationships
    account = relationship("TastytradeAccount", back_populates="orders")
    option = relationship("OptionInstrument", back_populates="orders")
    strategy = relationship("TradingStrategy", back_populates="orders")

class TradingStrategy(Base):
    """Multi-strategy management for options trading."""
    __tablename__ = "trading_strategies"
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("tastytrade_accounts.id"), nullable=False)
    name = Column(String(100), nullable=False)
    strategy_type = Column(Enum(StrategyType), nullable=False)
    description = Column(Text)
    
    # Capital Management
    allocated_capital = Column(Numeric(12, 2), nullable=False)  # Capital allocated to this strategy
    current_capital = Column(Numeric(12, 2), nullable=False)    # Current capital (after P&L)
    max_capital = Column(Numeric(12, 2))                        # Maximum capital limit
    target_capital = Column(Numeric(12, 2))                     # Target capital (e.g., $1M goal)
    
    # Performance Metrics
    total_pnl = Column(Numeric(12, 2), default=0)
    total_pnl_pct = Column(Numeric(8, 4), default=0)
    win_rate = Column(Numeric(5, 2))  # Percentage
    profit_factor = Column(Numeric(8, 4))  # Gross profit / Gross loss
    max_drawdown = Column(Numeric(8, 4))
    sharpe_ratio = Column(Numeric(8, 4))
    
    # Risk Management
    max_position_size = Column(Numeric(8, 4))  # Max % of capital per position
    profit_target_pct = Column(Numeric(5, 2), default=20)  # 20% profit taking
    stop_loss_pct = Column(Numeric(5, 2))
    max_dte = Column(Integer)  # Maximum days to expiration
    min_dte = Column(Integer)  # Minimum days to expiration
    
    # ATR Matrix specific settings
    atr_lookback_period = Column(Integer, default=14)
    risk_reward_ratio = Column(Numeric(4, 2))  # e.g., 2.0 for 2:1
    time_horizon_days = Column(Integer)  # Expected time to target from ATR analysis
    
    # Strategy Configuration (JSON string for flexibility)
    configuration = Column(Text)  # JSON string with strategy-specific settings
    
    # Status and automation
    is_active = Column(Boolean, default=True)
    is_automated = Column(Boolean, default=False)
    last_signal_at = Column(DateTime)
    next_review_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = relationship("TastytradeAccount", back_populates="strategies")
    positions = relationship("OptionPosition", back_populates="strategy")
    orders = relationship("OptionOrder", back_populates="strategy")
    signals = relationship("StrategySignal", back_populates="strategy")
    performance = relationship("StrategyPerformance", back_populates="strategy")

class StrategySignal(Base):
    """Trading signals generated by strategies."""
    __tablename__ = "strategy_signals"
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey("trading_strategies.id"), nullable=False)
    underlying_symbol = Column(String(20), nullable=False)
    signal_type = Column(String(50), nullable=False)  # ENTRY, EXIT, SCALE_OUT, etc.
    signal_strength = Column(Numeric(3, 2))  # 0.0 to 1.0
    
    # Signal details
    target_price = Column(Numeric(12, 4))
    stop_loss = Column(Numeric(12, 4))
    time_horizon_days = Column(Integer)
    risk_reward_ratio = Column(Numeric(4, 2))
    confidence_score = Column(Numeric(3, 2))
    
    # Options selection criteria
    target_delta = Column(Numeric(4, 3))  # For options selection
    max_dte = Column(Integer)
    min_dte = Column(Integer)
    target_strike_distance = Column(Numeric(5, 2))  # % OTM/ITM
    
    # Execution details
    recommended_action = Column(String(50))  # BUY_TO_OPEN, SELL_TO_OPEN, etc.
    position_size = Column(Numeric(12, 2))  # Dollar amount or % of capital
    is_executed = Column(Boolean, default=False)
    executed_at = Column(DateTime)
    execution_price = Column(Numeric(12, 4))
    
    # Performance tracking
    actual_return = Column(Numeric(8, 4))  # Actual return achieved
    days_held = Column(Integer)
    exit_reason = Column(String(50))  # PROFIT_TARGET, STOP_LOSS, EXPIRATION, etc.
    
    # Metadata
    signal_data = Column(Text)  # JSON with additional signal data (ATR, volatility, etc.)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # When signal expires
    
    # Relationships
    strategy = relationship("TradingStrategy", back_populates="signals")

class StrategyPerformance(Base):
    """Daily/periodic performance tracking for strategies."""
    __tablename__ = "strategy_performance"
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey("trading_strategies.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    
    # Portfolio metrics
    capital_value = Column(Numeric(12, 2), nullable=False)
    daily_pnl = Column(Numeric(12, 2))
    daily_pnl_pct = Column(Numeric(8, 4))
    cumulative_pnl = Column(Numeric(12, 2))
    cumulative_pnl_pct = Column(Numeric(8, 4))
    
    # Position metrics
    total_positions = Column(Integer)
    winning_positions = Column(Integer)
    losing_positions = Column(Integer)
    avg_win = Column(Numeric(12, 2))
    avg_loss = Column(Numeric(12, 2))
    
    # Risk metrics
    var_95 = Column(Numeric(12, 2))  # Value at Risk (95%)
    max_drawdown = Column(Numeric(8, 4))
    volatility = Column(Numeric(8, 4))
    
    # Greeks exposure
    total_delta = Column(Numeric(12, 4))
    total_gamma = Column(Numeric(12, 4))
    total_theta = Column(Numeric(12, 4))
    total_vega = Column(Numeric(12, 4))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    strategy = relationship("TradingStrategy", back_populates="performance")
    
    # Unique constraint on strategy and date
    __table_args__ = (
        Index('ix_performance_strategy_date', 'strategy_id', 'date', unique=True),
    )

class CapitalAllocation(Base):
    """Track capital allocation across strategies for automated scaling."""
    __tablename__ = "capital_allocations"
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("tastytrade_accounts.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("trading_strategies.id"), nullable=False)
    
    # Allocation details
    allocated_amount = Column(Numeric(12, 2), nullable=False)
    allocation_pct = Column(Numeric(5, 2), nullable=False)  # % of total capital
    min_allocation = Column(Numeric(12, 2))
    max_allocation = Column(Numeric(12, 2))
    
    # Performance-based adjustments
    performance_multiplier = Column(Numeric(4, 2), default=1.0)  # Adjust based on performance
    last_rebalance_at = Column(DateTime)
    next_rebalance_at = Column(DateTime)
    
    # Automation rules
    auto_scale_up = Column(Boolean, default=True)  # Auto increase on profits
    auto_scale_down = Column(Boolean, default=True)  # Auto decrease on losses
    scale_up_threshold = Column(Numeric(5, 2), default=20)  # % profit to trigger scale up
    scale_down_threshold = Column(Numeric(5, 2), default=-10)  # % loss to trigger scale down
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = relationship("TastytradeAccount")
    strategy = relationship("TradingStrategy")

class RiskMetrics(Base):
    """Portfolio-wide risk metrics for options trading."""
    __tablename__ = "risk_metrics"
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("tastytrade_accounts.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    
    # Portfolio Greeks
    portfolio_delta = Column(Numeric(12, 4))
    portfolio_gamma = Column(Numeric(12, 4))
    portfolio_theta = Column(Numeric(12, 4))
    portfolio_vega = Column(Numeric(12, 4))
    portfolio_rho = Column(Numeric(12, 4))
    
    # Risk measures
    var_95 = Column(Numeric(12, 2))  # Value at Risk (95% confidence)
    var_99 = Column(Numeric(12, 2))  # Value at Risk (99% confidence)
    expected_shortfall = Column(Numeric(12, 2))  # Expected loss beyond VaR
    max_loss_scenario = Column(Numeric(12, 2))  # Worst-case scenario loss
    
    # Concentration risks
    max_single_position_pct = Column(Numeric(5, 2))
    max_underlying_exposure_pct = Column(Numeric(5, 2))
    max_expiration_exposure_pct = Column(Numeric(5, 2))
    
    # Margin and liquidity
    margin_requirement = Column(Numeric(12, 2))
    excess_liquidity = Column(Numeric(12, 2))
    buying_power_used_pct = Column(Numeric(5, 2))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Index for time-series queries
    __table_args__ = (
        Index('ix_risk_account_date', 'account_id', 'date'),
    ) 