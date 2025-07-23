"""
QuantMatrix V2 Models - Clean Multi-User Architecture
====================================================

Base models and shared components for the V2 database schema.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.config import settings

# Base class for all models
Base = declarative_base()

# Database engine
engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency for getting database sessions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Import all models to ensure they're registered
from .users import *
from .accounts import *
from .instruments import *
from .positions import *
from .transactions import *
from .tax_lots import *
from .market_data import *
from .strategies import *
from .signals import *
from .notifications import *
from .audit import * 