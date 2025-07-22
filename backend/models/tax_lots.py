from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from typing import Optional, List

from .portfolio import Base

class TaxLotMethod(enum.Enum):
    """Tax lot accounting methods"""
    FIFO = "fifo"  # First In, First Out
    LIFO = "lifo"  # Last In, First Out
    HIFO = "hifo"  # Highest Cost First Out
    SPECIFIC = "specific"  # Specific identification

class TaxLot(Base):
    """Individual tax lot for tracking cost basis and tax implications"""
    __tablename__ = "tax_lots"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Reference to holding
    holding_id = Column(Integer, ForeignKey("holdings.id", ondelete="CASCADE"))
    
    # Tax lot details
    symbol = Column(String(10), nullable=False, index=True)
    account_id = Column(String(20), nullable=False)
    
    # Purchase information
    purchase_date = Column(DateTime, nullable=False)
    shares_purchased = Column(Float, nullable=False)
    cost_per_share = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)  # Includes fees/commissions
    commission = Column(Float, default=0.0)
    
    # Current status
    shares_remaining = Column(Float, nullable=False)  # After partial sales
    shares_sold = Column(Float, default=0.0)
    
    # Tax status
    is_long_term = Column(Boolean, default=False)  # > 1 year holding period
    is_wash_sale = Column(Boolean, default=False)
    wash_sale_amount = Column(Float, default=0.0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text)
    
    # Relationships
    holding = relationship("Holding", back_populates="tax_lots")
    sales = relationship("TaxLotSale", back_populates="tax_lot")
    
    @property
    def current_value(self) -> float:
        """Current market value of remaining shares"""
        if self.holding and self.holding.current_price:
            return self.shares_remaining * self.holding.current_price
        return 0.0
    
    @property
    def unrealized_gain_loss(self) -> float:
        """Unrealized gain/loss for remaining shares"""
        return self.current_value - (self.shares_remaining * self.cost_per_share)
    
    @property
    def unrealized_gain_loss_pct(self) -> float:
        """Unrealized gain/loss percentage"""
        cost_basis = self.shares_remaining * self.cost_per_share
        if cost_basis > 0:
            return (self.unrealized_gain_loss / cost_basis) * 100
        return 0.0
    
    @property
    def holding_period_days(self) -> int:
        """Number of days held"""
        return (datetime.utcnow() - self.purchase_date).days
    
    @property
    def tax_status(self) -> str:
        """Current tax status (short-term or long-term)"""
        return "long_term" if self.holding_period_days >= 365 else "short_term"

class TaxLotSale(Base):
    """Record of tax lot sales for realized gain/loss tracking"""
    __tablename__ = "tax_lot_sales"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Reference to original tax lot
    tax_lot_id = Column(Integer, ForeignKey("tax_lots.id", ondelete="CASCADE"))
    
    # Sale details
    sale_date = Column(DateTime, nullable=False)
    shares_sold = Column(Float, nullable=False)
    sale_price_per_share = Column(Float, nullable=False)
    total_proceeds = Column(Float, nullable=False)  # After fees/commissions
    commission = Column(Float, default=0.0)
    
    # Tax calculations
    cost_basis = Column(Float, nullable=False)  # Cost of shares sold
    realized_gain_loss = Column(Float, nullable=False)
    is_long_term = Column(Boolean, nullable=False)
    is_wash_sale = Column(Boolean, default=False)
    
    # Tax lot method used
    lot_method = Column(SQLEnum(TaxLotMethod), default=TaxLotMethod.FIFO)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    
    # Relationships
    tax_lot = relationship("TaxLot", back_populates="sales")
    
    @property
    def realized_gain_loss_pct(self) -> float:
        """Realized gain/loss percentage"""
        if self.cost_basis > 0:
            return (self.realized_gain_loss / self.cost_basis) * 100
        return 0.0

class TaxStrategy(Base):
    """Tax optimization strategies and recommendations"""
    __tablename__ = "tax_strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Strategy details
    account_id = Column(String(20), nullable=False)
    strategy_type = Column(String(50), nullable=False)  # tax_loss_harvesting, wash_sale_avoidance, etc.
    
    # Recommendations
    symbol = Column(String(10), nullable=False)
    action = Column(String(20), nullable=False)  # sell, hold, buy
    shares = Column(Float)
    target_price = Column(Float)
    
    # Tax impact
    estimated_tax_savings = Column(Float)
    estimated_tax_liability = Column(Float)
    confidence_score = Column(Float, default=0.0)  # 0-1 confidence in recommendation
    
    # Timing
    recommended_date = Column(DateTime)
    expiration_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    description = Column(Text)
    
class TaxReport(Base):
    """Tax reports and summaries"""
    __tablename__ = "tax_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Report details
    account_id = Column(String(20), nullable=False)
    report_type = Column(String(30), nullable=False)  # annual_summary, quarterly, tax_loss_harvesting
    tax_year = Column(Integer, nullable=False)
    
    # Summary data
    total_realized_gains = Column(Float, default=0.0)
    total_realized_losses = Column(Float, default=0.0)
    net_realized_gain_loss = Column(Float, default=0.0)
    
    short_term_gains = Column(Float, default=0.0)
    short_term_losses = Column(Float, default=0.0)
    long_term_gains = Column(Float, default=0.0)
    long_term_losses = Column(Float, default=0.0)
    
    # Unrealized positions
    total_unrealized_gains = Column(Float, default=0.0)
    total_unrealized_losses = Column(Float, default=0.0)
    
    # Tax calculations
    estimated_tax_liability = Column(Float, default=0.0)
    estimated_tax_rate = Column(Float, default=0.0)
    wash_sale_adjustments = Column(Float, default=0.0)
    
    # Metadata
    generated_at = Column(DateTime, default=datetime.utcnow)
    report_data = Column(Text)  # JSON data for detailed breakdown 