from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from backend.database import Base

class Dividend(Base):
    __tablename__ = "dividends"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    ex_date = Column(DateTime, nullable=False)
    pay_date = Column(DateTime, nullable=True)
    dividend_per_share = Column(Numeric(10, 4), nullable=False)
    total_dividend = Column(Numeric(15, 2), nullable=False)
    tax_withheld = Column(Numeric(15, 2), nullable=True, default=0)
    shares_held = Column(Numeric(15, 2), nullable=True)
    currency = Column(String(3), nullable=False, default="USD")
    source = Column(String(50), nullable=False, default="ibkr")
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # Relationships
    account = relationship("Account", back_populates="dividends")

    def __repr__(self):
        return f"<Dividend(symbol='{self.symbol}', amount='{self.total_dividend}', ex_date='{self.ex_date}')>" 