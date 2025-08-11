"""
Broker-Agnostic Portfolio Sync Service
======================================

Universal sync service that coordinates between different broker-specific services.
This service provides a unified interface for syncing portfolio data from any broker.

Architecture:
- IBKRSyncService: Handles IBKR FlexQuery and real-time API
- TastyTradeSyncService: Handles TastyTrade API  
- (Future) SchwabSyncService, FidelitySyncService, etc.

All broker-specific services populate the same broker-agnostic database models.
"""

import logging
from typing import Dict
from datetime import datetime

from backend.database import SessionLocal
from backend.models import BrokerAccount
from backend.services.portfolio.ibkr_sync_service import IBKRSyncService
from backend.services.portfolio.tastytrade_sync_service import TastyTradeSyncService

logger = logging.getLogger(__name__)


class BrokerSyncService:
    """
    Universal broker sync service that coordinates between broker-specific services.

    This service:
    1. Routes sync requests to appropriate broker-specific services
    2. Ensures all data is stored in broker-agnostic models
    3. Provides unified sync interface for frontend
    4. Handles account management and sync orchestration
    """

    def __init__(self):
        self.ibkr_sync = IBKRSyncService()
        self.tastytrade_sync = TastyTradeSyncService()

    async def sync_account(
        self, account_id: int, sync_type: str = "comprehensive"
    ) -> Dict:
        """
        Sync any broker account using the appropriate broker-specific service.

        Args:
            account_id: BrokerAccount.id in database
            sync_type: 'comprehensive', 'positions_only', 'transactions_only'
        """
        db = SessionLocal()
        try:
            # Get broker account
            broker_account = (
                db.query(BrokerAccount).filter(BrokerAccount.id == account_id).first()
            )
            if not broker_account:
                return {"error": f"Broker account {account_id} not found"}

            logger.info(
                f"🚀 Starting {sync_type} sync for {broker_account.broker} account {broker_account.account_number}"
            )

            # Route to appropriate broker service
            from backend.models.broker_account import BrokerType

            if broker_account.broker == BrokerType.IBKR:
                result = await self.ibkr_sync.sync_comprehensive_portfolio(
                    broker_account.account_number
                )
            elif broker_account.broker == BrokerType.TASTYTRADE:
                result = await self.tastytrade_sync.sync_account(db, broker_account)
            else:
                return {"error": f"Unsupported broker: {broker_account.broker}"}

            # Update sync status
            broker_account.last_successful_sync = datetime.now()
            from backend.models.broker_account import SyncStatus

            broker_account.sync_status = SyncStatus.SUCCESS
            broker_account.sync_error_message = None
            db.commit()

            return result

        except Exception as e:
            logger.error(f"❌ Error syncing account {account_id}: {e}")
            return {"error": str(e)}
        finally:
            db.close()

    async def sync_all_accounts(self, user_id: int) -> Dict:
        """Sync all broker accounts for a user."""
        db = SessionLocal()
        try:
            accounts = (
                db.query(BrokerAccount)
                .filter(
                    BrokerAccount.user_id == user_id, BrokerAccount.is_enabled == True
                )
                .all()
            )

            results = {}
            for account in accounts:
                account_key = f"{account.broker.value}_{account.account_number}"
                results[account_key] = await self.sync_account(account.id)

            return {
                "user_id": user_id,
                "accounts_synced": len(accounts),
                "results": results,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ Error syncing all accounts for user {user_id}: {e}")
            return {"error": str(e)}
        finally:
            db.close()


# Global instance
broker_sync_service = BrokerSyncService()
