from __future__ import annotations

from celery import shared_task
import asyncio
from backend.database import SessionLocal
from backend.services.portfolio.broker_sync_service import broker_sync_service
from backend.models.broker_account import BrokerAccount, BrokerType


@shared_task(name="backend.tasks.account_sync.sync_account_task")
def sync_account_task(account_id: int, sync_type: str = "comprehensive") -> dict:
    """Run broker account sync in a Celery worker (separate process)."""
    session = SessionLocal()
    try:
        # Run async sync in worker-owned event loop
        result = asyncio.run(
            broker_sync_service.sync_account_async(
                account_id=account_id, db=session, sync_type=sync_type
            )
        )
        return (
            result
            if isinstance(result, dict)
            else {"status": "success", "data": result}
        )
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        session.close()


@shared_task(name="backend.tasks.account_sync.sync_all_ibkr_accounts")
def sync_all_ibkr_accounts() -> dict:
    """Enqueue sync tasks for all enabled IBKR accounts."""
    session = SessionLocal()
    try:
        accounts = (
            session.query(BrokerAccount)
            .filter(
                BrokerAccount.broker == BrokerType.IBKR,
                BrokerAccount.is_enabled == True,
            )
            .all()
        )
        enqueued = 0
        results = []
        for acct in accounts:
            try:
                # Use existing Celery task to perform the heavy sync
                from backend.tasks.celery_app import celery_app

                task = celery_app.send_task(
                    "backend.tasks.account_sync.sync_account_task",
                    args=[acct.id, "comprehensive"],
                )
                results.append({"account_id": acct.id, "task_id": task.id})
                enqueued += 1
            except Exception as e:
                results.append({"account_id": acct.id, "error": str(e)})

        return {"status": "queued", "enqueued": enqueued, "results": results}
    finally:
        session.close()
