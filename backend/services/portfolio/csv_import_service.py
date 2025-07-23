"""
QuantMatrix V1 - CSV Import Service
Handles importing IBKR CSV files with proper models integration.

Supports the user's 3 CSV files:
- U19490886_20250401_20250722.csv (Taxable - Current)
- U19490886_20250331_20250331.csv (Taxable - Historical) 
- U15891532_20241015_20250722.csv (IRA - Transferred)
"""

import logging
import csv
import asyncio
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from decimal import Decimal
from pathlib import Path
import pandas as pd
from sqlalchemy.orm import Session

# Model imports
from backend.models.users import User
from backend.models.market_data import Instrument
from backend.models.csv_import import (
    CSVImportJob, 
    CSVTransactionRecord, 
    TaxLot,
    IBKR_CSV_IMPORT_CONFIGS,
    IBKRCSVImporter
)
from backend.database import SessionLocal

logger = logging.getLogger(__name__)

class CSVImportService:
    """
    CSV Import Service - Clean integration with models.
    Handles the user's 3 IBKR CSV files with proper tax lot calculations.
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or SessionLocal()
        self.importer = IBKRCSVImporter(self.db)
    
    async def import_user_csv_files(self, user_id: int, csv_directory: str = ".") -> Dict[str, Any]:
        """
        Import all 3 IBKR CSV files for the user.
        
        Args:
            user_id: User ID from users table
            csv_directory: Directory containing CSV files
            
        Returns:
            Comprehensive import results
        """
        logger.info(f"🚀 Starting CSV import for user {user_id}")
        
        # Verify user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found in users table")
        
        import_results = {}
        
        # Process each configured CSV file
        for config_key, config in IBKR_CSV_IMPORT_CONFIGS.items():
            try:
                file_path = Path(csv_directory) / config['filename']
                
                if not file_path.exists():
                    logger.warning(f"📁 CSV file not found: {file_path}")
                    import_results[config_key] = {
                        "status": "skipped",
                        "reason": "File not found",
                        "filename": config['filename']
                    }
                    continue
                
                logger.info(f"📊 Processing {config['description']}")
                
                # Import the CSV file
                result = await self.importer.import_csv_file(
                    user_id=user_id,
                    file_path=str(file_path),
                    filename=config['filename'],
                    import_config=config
                )
                
                import_results[config_key] = {
                    "status": "success",
                    "import_job_id": result.id,
                    "filename": config['filename'],
                    "description": config['description'],
                    "records_imported": result.records_imported,
                    "trades_imported": result.trades_imported,
                    "tax_lots_created": result.tax_lots_created,
                    "import_duration": result.processing_time_seconds,
                    "account_number": config['account_number'],
                    "tax_treatment": config['tax_treatment']
                }
                
                logger.info(f"✅ Completed {config['description']}: {result.records_imported} records")
                
            except Exception as e:
                logger.error(f"❌ Failed to import {config['filename']}: {e}")
                import_results[config_key] = {
                    "status": "error",
                    "filename": config['filename'],
                    "description": config['description'],
                    "error": str(e)
                }
        
        # Generate summary
        successful_imports = [r for r in import_results.values() if r.get("status") == "success"]
        total_records = sum(r.get("records_imported", 0) for r in successful_imports)
        total_tax_lots = sum(r.get("tax_lots_created", 0) for r in successful_imports)
        
        summary = {
            "user_id": user_id,
            "username": user.username,
            "import_results": import_results,
            "summary": {
                "total_files_configured": len(IBKR_CSV_IMPORT_CONFIGS),
                "successful_imports": len(successful_imports),
                "failed_imports": len(import_results) - len(successful_imports),
                "total_records_imported": total_records,
                "total_tax_lots_created": total_tax_lots
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"🎯 CSV import complete: {len(successful_imports)}/{len(IBKR_CSV_IMPORT_CONFIGS)} files, {total_records} records, {total_tax_lots} tax lots")
        
        return summary
    
    async def get_import_status(self, user_id: int) -> Dict[str, Any]:
        """Get status of CSV imports for a user."""
        try:
            # Get all import jobs for the user
            import_jobs = self.db.query(CSVImportJob).filter(
                CSVImportJob.user_id == user_id
            ).order_by(CSVImportJob.created_at.desc()).all()
            
            if not import_jobs:
                return {
                    "user_id": user_id,
                    "status": "no_imports",
                    "message": "No CSV imports found for this user"
                }
            
            # Summarize import status
            total_imports = len(import_jobs)
            successful_imports = [job for job in import_jobs if job.status == "completed"]
            failed_imports = [job for job in import_jobs if job.status == "failed"]
            
            # Get total records and tax lots
            total_records = sum(job.records_imported for job in successful_imports)
            total_tax_lots = sum(job.tax_lots_created for job in successful_imports)
            
            # Latest import details
            latest_import = import_jobs[0]
            
            return {
                "user_id": user_id,
                "status": "completed" if successful_imports else "failed",
                "summary": {
                    "total_imports": total_imports,
                    "successful_imports": len(successful_imports),
                    "failed_imports": len(failed_imports),
                    "total_records_imported": total_records,
                    "total_tax_lots_created": total_tax_lots
                },
                "latest_import": {
                    "filename": latest_import.filename,
                    "status": latest_import.status,
                    "created_at": latest_import.created_at.isoformat(),
                    "records_imported": latest_import.records_imported,
                    "tax_lots_created": latest_import.tax_lots_created
                },
                "all_imports": [
                    {
                        "id": job.id,
                        "filename": job.filename,
                        "status": job.status,
                        "created_at": job.created_at.isoformat(),
                        "records_imported": job.records_imported,
                        "tax_lots_created": job.tax_lots_created,
                        "error_message": job.error_message
                    }
                    for job in import_jobs
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting import status for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "status": "error",
                "error": str(e)
            }
    
    async def get_user_tax_lots(self, user_id: int, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get tax lots for a user, optionally filtered by symbol."""
        try:
            query = self.db.query(TaxLot).filter(TaxLot.user_id == user_id)
            
            if symbol:
                query = query.filter(TaxLot.symbol == symbol)
            
            tax_lots = query.order_by(TaxLot.acquisition_date.desc()).all()
            
            result = []
            for lot in tax_lots:
                result.append({
                    "lot_id": lot.id,
                    "symbol": lot.symbol,
                    "acquisition_date": lot.acquisition_date.isoformat(),
                    "quantity": float(lot.quantity),
                    "cost_per_share": float(lot.cost_per_share),
                    "current_price": float(lot.current_price) if lot.current_price else None,
                    "cost_basis": float(lot.cost_basis),
                    "current_value": float(lot.current_value) if lot.current_value else None,
                    "unrealized_pnl": float(lot.unrealized_pnl) if lot.unrealized_pnl else None,
                    "unrealized_pnl_pct": float(lot.unrealized_pnl_pct) if lot.unrealized_pnl_pct else None,
                    "days_held": lot.days_held,
                    "is_long_term": lot.is_long_term,
                    "tax_lot_method": lot.tax_lot_method,
                    "account_number": lot.account_number,
                    "account_type": lot.account_type
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting tax lots for user {user_id}: {e}")
            return []
    
    async def get_user_transactions(self, user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Get transaction records for a user."""
        try:
            transactions = self.db.query(CSVTransactionRecord).filter(
                CSVTransactionRecord.user_id == user_id
            ).order_by(CSVTransactionRecord.transaction_date.desc()).limit(limit).all()
            
            result = []
            for txn in transactions:
                result.append({
                    "record_id": txn.id,
                    "symbol": txn.symbol,
                    "transaction_date": txn.transaction_date.isoformat(),
                    "action": txn.action,
                    "quantity": float(txn.quantity),
                    "price": float(txn.price),
                    "amount": float(txn.amount),
                    "commission": float(txn.commission) if txn.commission else 0.0,
                    "currency": txn.currency,
                    "account_number": txn.account_number,
                    "description": txn.description,
                    "import_job_id": txn.import_job_id
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting transactions for user {user_id}: {e}")
            return []
    
    async def validate_csv_file(self, file_path: str) -> Dict[str, Any]:
        """Validate a CSV file before import."""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return {
                    "valid": False,
                    "error": "File not found"
                }
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > 50 * 1024 * 1024:  # 50MB limit
                return {
                    "valid": False,
                    "error": "File too large (>50MB)"
                }
            
            # Check file format
            if file_path.suffix.lower() != '.csv':
                return {
                    "valid": False,
                    "error": "File must be CSV format"
                }
            
            # Read and validate headers
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader, [])
            
            required_headers = ['Date', 'Symbol', 'Action', 'Quantity', 'Price']
            missing_headers = [h for h in required_headers if h not in headers]
            
            if missing_headers:
                return {
                    "valid": False,
                    "error": f"Missing required headers: {missing_headers}"
                }
            
            # Count rows
            with open(file_path, 'r', encoding='utf-8') as f:
                row_count = sum(1 for line in f) - 1  # Subtract header row
            
            return {
                "valid": True,
                "file_size_bytes": file_size,
                "estimated_records": row_count,
                "headers": headers
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}"
            }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def import_csv_files_for_user(user_id: int, csv_directory: str = ".") -> Dict[str, Any]:
    """Convenience function to import CSV files for a user."""
    service = CSVImportService()
    try:
        return await service.import_user_csv_files(user_id, csv_directory)
    finally:
        service.db.close()

async def get_user_import_status(user_id: int) -> Dict[str, Any]:
    """Convenience function to get import status for a user."""
    service = CSVImportService()
    try:
        return await service.get_import_status(user_id)
    finally:
        service.db.close()

async def get_user_tax_lots_summary(user_id: int) -> Dict[str, Any]:
    """Get summary of user's tax lots by symbol."""
    service = CSVImportService()
    try:
        tax_lots = await service.get_user_tax_lots(user_id)
        
        # Group by symbol
        by_symbol = {}
        total_cost_basis = 0
        total_current_value = 0
        
        for lot in tax_lots:
            symbol = lot['symbol']
            
            if symbol not in by_symbol:
                by_symbol[symbol] = {
                    'symbol': symbol,
                    'total_quantity': 0,
                    'total_cost_basis': 0,
                    'total_current_value': 0,
                    'lots_count': 0,
                    'average_cost_per_share': 0,
                    'total_unrealized_pnl': 0
                }
            
            by_symbol[symbol]['total_quantity'] += lot['quantity']
            by_symbol[symbol]['total_cost_basis'] += lot['cost_basis']
            by_symbol[symbol]['total_current_value'] += lot['current_value'] or 0
            by_symbol[symbol]['lots_count'] += 1
            by_symbol[symbol]['total_unrealized_pnl'] += lot['unrealized_pnl'] or 0
            
            total_cost_basis += lot['cost_basis']
            total_current_value += lot['current_value'] or 0
        
        # Calculate averages
        for symbol_data in by_symbol.values():
            if symbol_data['total_quantity'] > 0:
                symbol_data['average_cost_per_share'] = symbol_data['total_cost_basis'] / symbol_data['total_quantity']
        
        return {
            "user_id": user_id,
            "summary": {
                "total_symbols": len(by_symbol),
                "total_lots": len(tax_lots),
                "total_cost_basis": total_cost_basis,
                "total_current_value": total_current_value,
                "total_unrealized_pnl": total_current_value - total_cost_basis
            },
            "by_symbol": list(by_symbol.values()),
            "timestamp": datetime.now().isoformat()
        }
        
    finally:
        service.db.close() 