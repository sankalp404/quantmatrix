from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from . import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    # accounts = relationship("Account", back_populates="user")  # TODO: Add user_id to Account model if needed
    # portfolios = relationship("Portfolio", back_populates="user")  # TODO: Create Portfolio model if needed
    # alerts = relationship("Alert", back_populates="user")  # TODO: Check Alert model relationships


# Account class moved to portfolio.py to avoid conflicts 