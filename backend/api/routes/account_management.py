"""
Account Management API Routes
============================

API endpoints for managing broker accounts before syncing.

Flow:
1. User adds broker account credentials via UI
2. Backend stores account in broker_accounts table 
3. Backend can then sync that account's data
4. Subsequent syncs update existing data
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.database import get_db
from backend.models import BrokerAccount
from backend.models.broker_account import (
    BrokerType,
    AccountType,
    AccountStatus,
    SyncStatus,
)
from backend.services.portfolio.broker_sync_service import broker_sync_service

router = APIRouter(prefix="/api/v1/accounts", tags=["Accounts"])


# Pydantic models for API
class AddBrokerAccountRequest(BaseModel):
    broker: str  # 'IBKR', 'TASTYTRADE', etc.
    account_number: str
    account_name: Optional[str] = None
    account_type: str  # 'TAXABLE', 'TRADITIONAL_IRA', etc.
    api_credentials: Optional[dict] = None  # Store encrypted credentials
    is_paper_trading: bool = False


class BrokerAccountResponse(BaseModel):
    id: int
    broker: str
    account_number: str
    account_name: Optional[str]
    account_type: str
    status: str
    is_enabled: bool
    last_successful_sync: Optional[datetime]
    sync_status: Optional[str]
    created_at: datetime


class SyncAccountRequest(BaseModel):
    sync_type: str = (
        "comprehensive"  # 'comprehensive', 'positions_only', 'transactions_only'
    )


@router.post("/add", response_model=BrokerAccountResponse)
async def add_broker_account(
    request: AddBrokerAccountRequest,
    user_id: int = 1,  # TODO: Get from auth
    db: Session = Depends(get_db),
):
    """
    Add a new broker account for syncing.

    This must be done before syncing - users add their account credentials
    and then we can sync data from that account.
    """
    try:
        # Validate broker type
        try:
            broker_enum = BrokerType[request.broker.upper()]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported broker: {request.broker}. Supported: IBKR, TASTYTRADE",
            )

        # Validate account type
        try:
            account_type_enum = AccountType[request.account_type.upper()]
        except KeyError:
            raise HTTPException(
                status_code=400, detail=f"Invalid account type: {request.account_type}"
            )

        # Check if account already exists
        existing = (
            db.query(BrokerAccount)
            .filter(
                BrokerAccount.user_id == user_id,
                BrokerAccount.account_number == request.account_number,
                BrokerAccount.broker == broker_enum,
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Account {request.account_number} for {request.broker} already exists",
            )

        # Create new broker account
        broker_account = BrokerAccount(
            user_id=user_id,
            broker=broker_enum,
            account_number=request.account_number,
            account_name=request.account_name
            or f"{request.broker} {request.account_number}",
            account_type=account_type_enum,
            status=AccountStatus.ACTIVE,
            is_enabled=True,
            api_credentials_stored=request.api_credentials is not None,
            sync_status=SyncStatus.NEVER_SYNCED,
            currency="USD",  # Default, will be updated during sync
            margin_enabled=False,  # Will be updated during sync
            options_enabled=False,  # Will be updated during sync
            futures_enabled=False,  # Will be updated during sync
            created_at=datetime.now(),
        )

        db.add(broker_account)
        db.commit()
        db.refresh(broker_account)

        return BrokerAccountResponse(
            id=broker_account.id,
            broker=broker_account.broker.value,
            account_number=broker_account.account_number,
            account_name=broker_account.account_name,
            account_type=broker_account.account_type.value,
            status=broker_account.status.value,
            is_enabled=broker_account.is_enabled,
            last_successful_sync=broker_account.last_successful_sync,
            sync_status=(
                broker_account.sync_status.value if broker_account.sync_status else None
            ),
            created_at=broker_account.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error adding account: {str(e)}")


@router.get("", response_model=List[BrokerAccountResponse])
async def list_broker_accounts(
    user_id: int = 1, db: Session = Depends(get_db)  # TODO: Get from auth
):
    """List all broker accounts for the user."""
    accounts = db.query(BrokerAccount).filter(BrokerAccount.user_id == user_id).all()

    return [
        BrokerAccountResponse(
            id=account.id,
            broker=account.broker.value,
            account_number=account.account_number,
            account_name=account.account_name,
            account_type=account.account_type.value,
            status=account.status.value,
            is_enabled=account.is_enabled,
            last_successful_sync=account.last_successful_sync,
            sync_status=account.sync_status.value if account.sync_status else None,
            created_at=account.created_at,
        )
        for account in accounts
    ]


@router.post("/{account_id}/sync")
async def sync_broker_account(
    account_id: int,
    request: SyncAccountRequest,
    user_id: int = 1,  # TODO: Get from auth
    db: Session = Depends(get_db),
):
    """
    Sync a specific broker account.

    This populates all database tables with data from the broker.
    Account must be added first via /add endpoint.
    """
    try:
        # Verify account belongs to user
        account = (
            db.query(BrokerAccount)
            .filter(BrokerAccount.id == account_id, BrokerAccount.user_id == user_id)
            .first()
        )

        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        if not account.is_enabled:
            raise HTTPException(status_code=400, detail="Account is disabled")

        # Update sync status
        account.sync_status = SyncStatus.IN_PROGRESS
        account.last_sync_attempt = datetime.now()
        db.commit()

        # Perform sync
        result = await broker_sync_service.sync_account(account_id, request.sync_type)

        # Update status based on result
        if "error" in result:
            account.sync_status = SyncStatus.FAILED
            account.sync_error_message = result["error"]
        else:
            account.sync_status = SyncStatus.COMPLETED
            account.last_successful_sync = datetime.now()
            account.sync_error_message = None

        db.commit()
        return result

    except HTTPException:
        raise
    except Exception as e:
        account.sync_status = SyncStatus.FAILED
        account.sync_error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/sync-all")
async def sync_all_accounts(
    user_id: int = 1, db: Session = Depends(get_db)  # TODO: Get from auth
):
    """Sync all enabled broker accounts for the user."""
    try:
        result = await broker_sync_service.sync_all_accounts(user_id)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing accounts: {str(e)}")


@router.delete("/{account_id}")
async def delete_broker_account(
    account_id: int,
    user_id: int = 1,  # TODO: Get from auth
    db: Session = Depends(get_db),
):
    """Delete a broker account (soft delete - disable it)."""
    try:
        account = (
            db.query(BrokerAccount)
            .filter(BrokerAccount.id == account_id, BrokerAccount.user_id == user_id)
            .first()
        )

        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Soft delete - just disable the account
        account.is_enabled = False
        account.status = AccountStatus.INACTIVE
        account.updated_at = datetime.now()

        db.commit()
        return {"message": f"Account {account.account_number} disabled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting account: {str(e)}")
