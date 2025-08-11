"""
Celery Tasks for Transaction Data Syncing
Background tasks to sync transaction data from IBKR
"""

import logging
from datetime import datetime

from backend.tasks.celery_app import celery_app
from backend.services.transaction_sync import transaction_sync_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def sync_all_account_transactions(self, days: int = 365):
    """Background task to sync transaction data for all accounts."""
    try:
        logger.info(f"Starting transaction sync for all accounts ({days} days)")

        # This will be async, but Celery handles it
        import asyncio

        result = asyncio.run(transaction_sync_service.sync_all_accounts(days))

        logger.info(f"Transaction sync completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Error in sync_all_account_transactions task: {e}")
        raise self.retry(exc=e, countdown=300, max_retries=3)  # Retry after 5 minutes


@celery_app.task(bind=True)
def sync_account_transactions(self, account_number: str, days: int = 365):
    """Background task to sync transaction data for a specific account."""
    try:
        logger.info(
            f"Starting transaction sync for account {account_number} ({days} days)"
        )

        import asyncio

        result = asyncio.run(
            transaction_sync_service.sync_account_transactions(account_number, days)
        )

        logger.info(f"Transaction sync completed for {account_number}: {result}")
        return result

    except Exception as e:
        logger.error(
            f"Error in sync_account_transactions task for {account_number}: {e}"
        )
        raise self.retry(exc=e, countdown=300, max_retries=3)


@celery_app.task
def daily_transaction_sync():
    """Daily scheduled task to sync transaction data."""
    try:
        logger.info("Starting daily transaction sync")

        # Sync last 30 days of data daily
        result = sync_all_account_transactions.delay(days=30)

        return {
            "status": "initiated",
            "task_id": result.id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in daily_transaction_sync: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task
def weekly_full_transaction_sync():
    """Weekly scheduled task to do a full transaction sync."""
    try:
        logger.info("Starting weekly full transaction sync")

        # Sync last 365 days of data weekly
        result = sync_all_account_transactions.delay(days=365)

        return {
            "status": "initiated",
            "task_id": result.id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in weekly_full_transaction_sync: {e}")
        return {"status": "error", "error": str(e)}
