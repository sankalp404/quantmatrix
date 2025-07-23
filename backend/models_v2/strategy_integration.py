"""
Strategy Integration Layer - V2 Enhanced
========================================

Connects existing strategy services (ATR Options, DCA, etc.) with V2 models
for seamless strategy management through StrategiesManager.tsx
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from . import Base
from .strategies import Strategy, StrategyRun, StrategyType

# =============================================================================
# STRATEGY SERVICE REGISTRY
# =============================================================================

class StrategyServiceType(enum.Enum):
    ATR_OPTIONS = "atr_options_strategy"
    DCA_STRATEGY = "dca_strategy"
    MOMENTUM = "momentum_strategy"
    PAIRS_TRADING = "pairs_trading"
    COVERED_CALL = "covered_call"
    IRON_CONDOR = "iron_condor"

class StrategyService(Base):
    """Registry of available strategy services and their configurations."""
    __tablename__ = "strategy_services_v2"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_type = Column(String(50), unique=True, nullable=False)  # matches StrategyServiceType
    display_name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Service Configuration
    service_module = Column(String(200), nullable=False)  # e.g., "backend.services.atr_options_strategy"
    service_class = Column(String(100), nullable=False)   # e.g., "ATROptionsStrategy"
    
    # UI Configuration for StrategiesManager.tsx
    category = Column(String(20), nullable=False)  # "stocks", "options"
    complexity = Column(String(20), nullable=False)  # "beginner", "intermediate", "advanced"
    min_capital = Column(DECIMAL(15, 2), nullable=False)
    expected_return_annual = Column(String(50))  # "15-25%"
    max_drawdown = Column(String(20))  # "8-12%"
    time_horizon = Column(String(50))  # "1-45 days"
    
    # Supported Parameters (JSON schema for UI generation)
    supported_parameters = Column(JSON)  # Dynamic form fields for StrategiesManager
    default_parameters = Column(JSON)    # Default values
    
    # Availability
    is_available = Column(Boolean, default=True)
    requires_approval = Column(Boolean, default=False)
    
    # Performance Tracking
    success_rate = Column(DECIMAL(5, 2))  # Historical success rate
    avg_return = Column(DECIMAL(8, 4))    # Average historical return
    
    # Audit
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

# =============================================================================
# STRATEGY EXECUTION PARAMETERS
# =============================================================================

class StrategyExecution(Base):
    """Execution parameters for strategy instances."""
    __tablename__ = "strategy_executions_v2"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, ForeignKey("strategies_v2.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users_v2.id"), nullable=False)
    
    # Execution Configuration (from StrategiesManager.tsx)
    brokerage = Column(String(20), nullable=False)  # "tastytrade", "ibkr"
    account_number = Column(String(50))
    
    # Capital Management
    allocated_capital = Column(DECIMAL(15, 2), nullable=False)
    current_capital = Column(DECIMAL(15, 2), nullable=False)
    profit_target_pct = Column(DECIMAL(5, 2), default=20.0)
    stop_loss_pct = Column(DECIMAL(5, 2), default=10.0)
    reinvest_profit_pct = Column(DECIMAL(5, 2), default=80.0)
    
    # Automation Settings
    is_automated = Column(Boolean, default=True)
    max_positions = Column(Integer, default=10)
    position_size_pct = Column(DECIMAL(5, 2), default=5.0)
    
    # Performance Tracking
    total_pnl = Column(DECIMAL(15, 2), default=0)
    total_pnl_pct = Column(DECIMAL(8, 4), default=0)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    
    # Execution State
    last_execution = Column(DateTime)
    next_execution = Column(DateTime)
    execution_frequency = Column(String(20), default="daily")  # daily, hourly, weekly
    
    # Strategy-Specific Parameters (JSON for flexibility)
    strategy_parameters = Column(JSON)  # Stores strategy-specific config
    
    # Audit
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    strategy = relationship("Strategy", backref="executions")
    user = relationship("User", backref="strategy_executions")

# =============================================================================
# PREDEFINED STRATEGY SERVICES
# =============================================================================

STRATEGY_SERVICE_DEFINITIONS = [
    {
        "service_type": "atr_options_strategy",
        "display_name": "ATR Matrix Options",
        "description": "Automated options trading using ATR Matrix signals with time horizon-based execution. Targets 20% monthly returns.",
        "service_module": "backend.services.atr_options_strategy",
        "service_class": "ATROptionsStrategy",
        "category": "options",
        "complexity": "advanced",
        "min_capital": 10000,
        "expected_return_annual": "15-25% monthly",
        "max_drawdown": "8-12%",
        "time_horizon": "1-45 days",
        "supported_parameters": {
            "profit_target_pct": {"type": "number", "min": 10, "max": 50, "default": 20},
            "stop_loss_pct": {"type": "number", "min": 5, "max": 50, "default": 50},
            "max_dte": {"type": "number", "min": 7, "max": 90, "default": 45},
            "min_dte": {"type": "number", "min": 1, "max": 14, "default": 7},
            "target_delta_range": {"type": "range", "min": 0.2, "max": 0.8, "default": [0.3, 0.7]},
            "max_position_size_pct": {"type": "number", "min": 1, "max": 10, "default": 5}
        },
        "default_parameters": {
            "profit_target_pct": 20.0,
            "stop_loss_pct": 50.0,
            "max_dte": 45,
            "min_dte": 7,
            "target_delta_range": [0.3, 0.7],
            "max_position_size_pct": 5.0
        },
        "is_available": True
    },
    {
        "service_type": "dca_strategy",
        "display_name": "DCA Strategy Suite",
        "description": "Multiple renowned DCA strategies (Graham, Buffett, Lynch, Dalio) with real market data analysis.",
        "service_module": "backend.services.dca_strategy",
        "service_class": "DCAStrategyService",
        "category": "stocks",
        "complexity": "intermediate",
        "min_capital": 5000,
        "expected_return_annual": "12-18%",
        "max_drawdown": "5-8%",
        "time_horizon": "3-30 days",
        "supported_parameters": {
            "strategy_type": {"type": "select", "options": ["conservative", "standard", "aggressive", "balanced"], "default": "standard"},
            "rebalance_frequency": {"type": "select", "options": ["daily", "weekly", "monthly"], "default": "weekly"},
            "max_position_increase_pct": {"type": "number", "min": 5, "max": 25, "default": 15},
            "profit_taking_threshold": {"type": "number", "min": 20, "max": 100, "default": 50}
        },
        "default_parameters": {
            "strategy_type": "standard",
            "rebalance_frequency": "weekly",
            "max_position_increase_pct": 15.0,
            "profit_taking_threshold": 50.0
        },
        "is_available": True
    }
]

# =============================================================================
# STRATEGY INTEGRATION HELPERS
# =============================================================================

async def initialize_strategy_service(
    user_id: int,
    service_type: str,
    execution_params: dict,
    db_session
) -> dict:
    """Initialize a strategy service with user parameters from StrategiesManager.tsx"""
    
    # Get service definition
    service = db_session.query(StrategyService).filter(
        StrategyService.service_type == service_type
    ).first()
    
    if not service:
        raise ValueError(f"Strategy service {service_type} not found")
    
    # Create strategy record
    strategy = Strategy(
        user_id=user_id,
        name=f"{service.display_name} - {execution_params.get('brokerage', 'default')}",
        strategy_type=service_type,
        description=service.description,
        allocated_capital=execution_params.get('allocated_capital', service.min_capital),
        max_positions=execution_params.get('max_positions', 10),
        profit_target_pct=execution_params.get('profit_target_pct', 20.0),
        stop_loss_pct=execution_params.get('stop_loss_pct', 10.0),
        is_active=True
    )
    
    db_session.add(strategy)
    db_session.flush()
    
    # Create execution record
    execution = StrategyExecution(
        strategy_id=strategy.id,
        user_id=user_id,
        brokerage=execution_params.get('brokerage', 'tastytrade'),
        account_number=execution_params.get('account_number'),
        allocated_capital=execution_params.get('allocated_capital'),
        current_capital=execution_params.get('allocated_capital'),
        profit_target_pct=execution_params.get('profit_target_pct', 20.0),
        stop_loss_pct=execution_params.get('stop_loss_pct', 10.0),
        reinvest_profit_pct=execution_params.get('reinvest_profit_pct', 80.0),
        is_automated=execution_params.get('is_automated', True),
        strategy_parameters=execution_params.get('strategy_parameters', service.default_parameters)
    )
    
    db_session.add(execution)
    db_session.commit()
    
    return {
        "strategy_id": strategy.id,
        "execution_id": execution.id,
        "status": "initialized",
        "message": f"{service.display_name} initialized with ${execution_params.get('allocated_capital'):,}"
    } 