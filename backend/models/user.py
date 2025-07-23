"""
User Management Models
===========================

Multi-user authentication, preferences, and user isolation.
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Text, 
    ForeignKey, UniqueConstraint, Index, CheckConstraint,
    TIMESTAMP, Enum as SQLEnum, JSON, DECIMAL
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from . import Base

# =============================================================================
# ENUMS
# =============================================================================

class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"

# =============================================================================
# USER MANAGEMENT
# =============================================================================

class User(Base):
    """User accounts with authentication and preferences."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255))  # OAuth users may not have password
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(20))
    
    # Authentication & Access
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    last_login = Column(TIMESTAMP(timezone=True))
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(TIMESTAMP(timezone=True))
    
    # Preferences
    timezone = Column(String(50), default="UTC")
    currency_preference = Column(String(3), default="USD")
    notification_preferences = Column(JSON)
    
    # Audit
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships - Fixed to only include existing models
    strategies = relationship("Strategy", back_populates="user", foreign_keys="[Strategy.user_id]", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", foreign_keys="[Notification.user_id]", cascade="all, delete-orphan")
    # Note: Signals are related to strategies, not directly to users
    
    __table_args__ = (
        Index('idx_users_email_active', 'email', 'is_active'),
        Index('idx_users_last_login', 'last_login'),    ) 