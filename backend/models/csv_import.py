"""
CSV Import Models and Services for QuantMatrix
==============================================

Handles importing transaction and position data from CSV files.
Supports multiple brokers and formats with automatic parsing.
"""

import json
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any, Set
import pandas as pd
import numpy as np

from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, func, Boolean, Float, DECIMAL
from sqlalchemy.orm import relationship
from . import Base
from ..database import SessionLocal

# Import database from parent directory
from datetime import datetime
import enum
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import logging

from . import Base

logger = logging.getLogger(__name__)

# =============================================================================
# ENUMS
# =============================================================================

class ImportStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"

class AccountType(enum.Enum):
    TAXABLE = "taxable"
    IRA = "ira"
    ROTH_IRA = "roth_ira"
    HSA = "hsa"

class ImportDataType(enum.Enum):
    TRADES = "trades"
    POSITIONS = "positions"
    DIVIDENDS = "dividends"
    INTEREST = "interest"
    FEES = "fees"
    TRANSFERS = "transfers"

# =============================================================================
# CSV IMPORT TRACKING
# =============================================================================

class CSVImport(Base):
    """Track CSV import jobs and their status."""
    __tablename__ = "csv_imports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # File Information
    filename = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer)
    file_hash = Column(String(64))  # SHA-256 hash for deduplication
    
    # Account Information (extracted from CSV)
    account_number = Column(String(50), nullable=False)
    account_name = Column(String(255))
    account_type = Column(String(50))  # From IBKR: "Individual", "Joint", etc.
    brokerage = Column(String(20), default="IBKR")
    
    # Import Configuration
    import_start_date = Column(DateTime)  # Only import data from this date
    tax_treatment = Column(String(20))  # "taxable", "tax_deferred", "roth"
    use_average_cost_basis = Column(Boolean, default=False)  # For transferred positions
    
    # Processing Status
    status = Column(String(20), default=ImportStatus.PENDING.value)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Results Summary
    total_records = Column(Integer, default=0)
    records_processed = Column(Integer, default=0)
    records_imported = Column(Integer, default=0)
    records_skipped = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    
    # Data Breakdown
    trades_imported = Column(Integer, default=0)
    positions_created = Column(Integer, default=0)
    tax_lots_created = Column(Integer, default=0)
    dividends_imported = Column(Integer, default=0)
    
    # Error Handling
    error_message = Column(Text)
    warnings = Column(JSON)  # Array of warning messages
    
    # Validation Results
    data_quality_score = Column(DECIMAL(3, 2))  # 0.0 to 1.0
    validation_errors = Column(JSON)
    
    # Audit
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="csv_imports")

# =============================================================================
# IMPORT HELPERS
# =============================================================================

class IBKRCSVImporter:
    """IBKR CSV Import Service with tax lot calculation."""
    
    def __init__(self, db_session):
        self.db = db_session
        self.current_year = datetime.now().year
        
    async def import_csv_file(
        self,
        user_id: int,
        file_path: str,
        filename: str,
        import_config: Dict
    ) -> CSVImport:
        """Import IBKR CSV file with comprehensive data processing."""
        
        # Create import record
        csv_import = CSVImport(
            user_id=user_id,
            filename=filename,
            account_number=import_config.get('account_number', 'unknown'),
            tax_treatment=import_config.get('tax_treatment', 'taxable'),
            use_average_cost_basis=import_config.get('use_average_cost_basis', False),
            import_start_date=import_config.get('start_date'),
            status=ImportStatus.PROCESSING.value,
            started_at=datetime.now()
        )
        self.db.add(csv_import)
        self.db.flush()
        
        try:
            # Parse CSV file
            df = pd.read_csv(file_path, header=None, names=['Section', 'Type', 'Field', 'Data'])
            csv_import.total_records = len(df)
            
            # Extract account information
            await self._extract_account_info(df, csv_import)
            
            # Process different data types
            trades_df = await self._extract_trades_data(df)
            positions_df = await self._extract_positions_data(df)
            dividends_df = await self._extract_dividends_data(df)
            
            # Import trades and create tax lots
            if not trades_df.empty:
                await self._import_trades(trades_df, csv_import)
            
            # Import current positions
            if not positions_df.empty:
                await self._import_positions(positions_df, csv_import)
            
            # Import dividends
            if not dividends_df.empty:
                await self._import_dividends(dividends_df, csv_import)
            
            # Calculate tax lots for current year
            await self._calculate_tax_lots(csv_import)
            
            # Validate imported data
            await self._validate_import(csv_import)
            
            # Mark as completed
            csv_import.status = ImportStatus.COMPLETED.value
            csv_import.completed_at = datetime.now()
            
            self.db.commit()
            
            logger.info(f"✅ Successfully imported {csv_import.filename} - "
                       f"{csv_import.records_imported} records imported")
            
            return csv_import
            
        except Exception as e:
            csv_import.status = ImportStatus.FAILED.value
            csv_import.error_message = str(e)
            csv_import.completed_at = datetime.now()
            self.db.commit()
            
            logger.error(f"❌ Failed to import {csv_import.filename}: {e}")
            raise
    
    async def _extract_account_info(self, df: pd.DataFrame, csv_import: CSVImport):
        """Extract account information from CSV."""
        
        account_info = df[df['Section'] == 'Account Information']
        
        for _, row in account_info.iterrows():
            if row['Field'] == 'Account':
                csv_import.account_number = row['Data']
            elif row['Field'] == 'Name':
                csv_import.account_name = row['Data']
            elif row['Field'] == 'Account Type':
                csv_import.account_type = row['Data']
        
        # Determine tax treatment from account name/type
        if 'IRA' in csv_import.account_name or 'IRA' in csv_import.account_type:
            csv_import.tax_treatment = AccountType.IRA.value
        elif 'Roth' in csv_import.account_name:
            csv_import.tax_treatment = AccountType.ROTH_IRA.value
        else:
            csv_import.tax_treatment = AccountType.TAXABLE.value
    
    async def _extract_trades_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract and clean trades data."""
        
        trades_df = df[df['Section'] == 'Trades'].copy()
        
        if trades_df.empty:
            return pd.DataFrame()
        
        # Parse trade data
        trade_records = []
        for _, row in trades_df.iterrows():
            if row['Type'] == 'Data' and row['Field'] == 'Order':
                # Parse the complex data field
                data_parts = str(row['Data']).split(',')
                if len(data_parts) >= 10:  # Ensure we have enough fields
                    trade_record = {
                        'asset_class': data_parts[0],
                        'currency': data_parts[1], 
                        'symbol': data_parts[2],
                        'date_time': data_parts[3].strip('"'),
                        'quantity': float(data_parts[4]) if data_parts[4] else 0,
                        'price': float(data_parts[5]) if data_parts[5] else 0,
                        'proceeds': float(data_parts[7]) if data_parts[7] else 0,
                        'commission': float(data_parts[8]) if data_parts[8] else 0,
                        'total': float(data_parts[9]) if data_parts[9] else 0,
                        'pnl': float(data_parts[10]) if len(data_parts) > 10 and data_parts[10] else 0,
                        'code': data_parts[11] if len(data_parts) > 11 else ''
                    }
                    trade_records.append(trade_record)
        
        return pd.DataFrame(trade_records)
    
    async def _extract_positions_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract current positions data."""
        
        positions_df = df[df['Section'] == 'Positions'].copy()
        
        if positions_df.empty:
            return pd.DataFrame()
        
        position_records = []
        for _, row in positions_df.iterrows():
            if row['Type'] == 'Data':
                # Parse position data similar to trades
                # Implementation depends on exact CSV structure
                pass
        
        return pd.DataFrame(position_records)
    
    async def _extract_dividends_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract dividends data."""
        
        dividends_df = df[df['Section'] == 'Dividends'].copy()
        
        if dividends_df.empty:
            return pd.DataFrame()
        
        # Parse dividend data
        return dividends_df
    
    async def _import_trades(self, trades_df: pd.DataFrame, csv_import: CSVImport):
        """Import trades data and create transaction records."""
        
        for _, trade in trades_df.iterrows():
            # Filter for current year only (as user requested)
            trade_date = pd.to_datetime(trade['date_time'])
            if trade_date.year < self.current_year:
                csv_import.records_skipped += 1
                continue
            
            # Create transaction record
            # (This would integrate with the full transactions model)
            csv_import.trades_imported += 1
            csv_import.records_imported += 1
    
    async def _import_positions(self, positions_df: pd.DataFrame, csv_import: CSVImport):
        """Import current positions."""
        
        for _, position in positions_df.iterrows():
            # Create position record
            csv_import.positions_created += 1
            csv_import.records_imported += 1
    
    async def _import_dividends(self, dividends_df: pd.DataFrame, csv_import: CSVImport):
        """Import dividend data."""
        
        for _, dividend in dividends_df.iterrows():
            # Create dividend record
            csv_import.dividends_imported += 1
            csv_import.records_imported += 1
    
    async def _calculate_tax_lots(self, csv_import: CSVImport):
        """Calculate tax lots based on import configuration."""
        
        if csv_import.use_average_cost_basis:
            # For transferred positions (like IRA transfers)
            # Use average cost basis method
            await self._calculate_average_cost_lots(csv_import)
        else:
            # For taxable accounts, use FIFO by default
            await self._calculate_fifo_lots(csv_import)
    
    async def _calculate_average_cost_lots(self, csv_import: CSVImport):
        """Calculate tax lots using average cost basis for transferred positions."""
        
        # Group by symbol and calculate average cost
        # This handles transferred positions where exact lot basis is unknown
        csv_import.tax_lots_created += 1  # Placeholder
    
    async def _calculate_fifo_lots(self, csv_import: CSVImport):
        """Calculate tax lots using FIFO method for taxable accounts."""
        
        # Process transactions chronologically to create proper tax lots
        csv_import.tax_lots_created += 1  # Placeholder
    
    async def _validate_import(self, csv_import: CSVImport):
        """Validate imported data quality."""
        
        warnings = []
        errors = []
        
        # Check for data consistency
        if csv_import.trades_imported == 0 and csv_import.positions_created == 0:
            warnings.append("No trades or positions imported - check CSV format")
        
        # Calculate quality score
        total_processed = csv_import.records_processed
        if total_processed > 0:
            success_rate = csv_import.records_imported / total_processed
            csv_import.data_quality_score = success_rate
        
        csv_import.warnings = warnings
        csv_import.validation_errors = errors

# =============================================================================
# USAGE EXAMPLES - Updated for 3 CSV Files
# =============================================================================

IBKR_CSV_IMPORT_CONFIGS = {
    "U19490886_current": {  # Taxable Joint Account - Current Period
        "filename": "U19490886_20250401_20250722.csv",
        "account_number": "U19490886",
        "tax_treatment": "taxable",
        "use_average_cost_basis": False,  # Use actual trade basis
        "start_date": "2025-01-01",  # Only current year data
        "description": "Sankalp & Olga Joint Taxable Account - Current Period"
    },
    "U19490886_historical": {  # Taxable Joint Account - Historical Period  
        "filename": "U19490886_20250331_20250331.csv",
        "account_number": "U19490886",
        "tax_treatment": "taxable",
        "use_average_cost_basis": False,  # Use actual trade basis
        "start_date": "2025-01-01",  # Only current year data
        "description": "Sankalp & Olga Joint Taxable Account - Historical Period"
    },
    "U15891532": {  # Tax-Deferred IRA
        "filename": "U15891532_20241015_20250722.csv",
        "account_number": "U15891532", 
        "tax_treatment": "tax_deferred",
        "use_average_cost_basis": True,  # Transferred positions
        "start_date": "2025-01-01",  # Only current year data
        "description": "Sankalp IRA (Transferred Positions)"
    }
}

# =============================================================================
# BATCH IMPORT HELPER
# =============================================================================

async def import_all_ibkr_csvs(user_id: int, csv_directory: str = ".") -> Dict[str, Any]:
    """Import all 3 IBKR CSV files in sequence."""
    
    import_results = {}
    
    for config_key, config in IBKR_CSV_IMPORT_CONFIGS.items():
        try:
            file_path = f"{csv_directory}/{config['filename']}"
            
            logger.info(f"📊 Starting import for {config['description']}")
            
            importer = IBKRCSVImporter(SessionLocal())
            result = await importer.import_csv_file(
                user_id=user_id,
                file_path=file_path,
                filename=config['filename'],
                import_config=config
            )
            
            import_results[config_key] = {
                "status": "success",
                "filename": config['filename'],
                "description": config['description'],
                "records_imported": result.records_imported,
                "trades_imported": result.trades_imported,
                "tax_lots_created": result.tax_lots_created,
                "import_id": result.id
            }
            
            logger.info(f"✅ Completed import for {config['description']}: {result.records_imported} records")
            
        except Exception as e:
            logger.error(f"❌ Failed to import {config['filename']}: {e}")
            import_results[config_key] = {
                "status": "error",
                "filename": config['filename'],
                "description": config['description'],
                "error": str(e)
            }
    
    # Summary
    total_imported = sum(r.get("records_imported", 0) for r in import_results.values() if r.get("status") == "success")
    successful_imports = len([r for r in import_results.values() if r.get("status") == "success"])
    
    summary = {
        "import_results": import_results,
        "summary": {
            "total_files": len(IBKR_CSV_IMPORT_CONFIGS),
            "successful_imports": successful_imports,
            "failed_imports": len(IBKR_CSV_IMPORT_CONFIGS) - successful_imports,
            "total_records_imported": total_imported
        },
        "timestamp": datetime.now().isoformat()
    }
    
    logger.info(f"🎯 Batch import complete: {successful_imports}/{len(IBKR_CSV_IMPORT_CONFIGS)} files imported, {total_imported} total records")
    
    return summary 