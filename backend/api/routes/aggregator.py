from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
import hashlib
import urllib.parse

from backend.database import get_db
from backend.api.routes.auth import get_current_user
from backend.models.user import User
from backend.models.broker_account import BrokerAccount, AccountCredentials
from backend.services.aggregator.schwab_connector import SchwabConnector
from backend.services.security.oauth_state import oauth_state_service
from backend.services.security.credential_vault import credential_vault
from backend.config import settings
from backend.services.security.pkce_state import (
    generate_code_verifier,
    compute_code_challenge,
    save_verifier_for_state,
    pop_verifier_for_state,
)


router = APIRouter()

def _is_truthy_value(val: Optional[str]) -> bool:
    if not val:
        return False
    v = str(val).strip().lower()
    return v not in {"", "none", "null", "false"}

def _is_schwab_configured() -> bool:
    return _is_truthy_value(settings.SCHWAB_CLIENT_ID) and _is_truthy_value(settings.SCHWAB_REDIRECT_URI)

class ProviderConfig(BaseModel):
    configured: bool
    redirect_uri: Optional[str] = None

class AggregatorConfigResponse(BaseModel):
    schwab: ProviderConfig

@router.get("/config", response_model=AggregatorConfigResponse)
async def get_aggregator_config() -> AggregatorConfigResponse:
    """Return minimal provider configuration status (no secrets)."""
    schwab_cfg = ProviderConfig(
        configured=_is_schwab_configured(),
        redirect_uri=(settings.SCHWAB_REDIRECT_URI if _is_truthy_value(settings.SCHWAB_REDIRECT_URI) else None),
    )
    return AggregatorConfigResponse(schwab=schwab_cfg)


class BrokersResponse(BaseModel):
    brokers: List[str]


@router.post("/brokers", response_model=BrokersResponse)
async def list_brokers() -> BrokersResponse:
    return BrokersResponse(brokers=["schwab"])


class LinkRequest(BaseModel):
    account_id: int
    trading: Optional[bool] = False


class LinkResponse(BaseModel):
    url: str


@router.post("/schwab/link", response_model=LinkResponse)
async def schwab_link(
    req: LinkRequest, user: User = Depends(get_current_user)
) -> LinkResponse:
    # Verify account ownership
    # Note: account_management uses user_id=1 for now; auth is enforced here
    if not req.account_id:
        raise HTTPException(status_code=400, detail="account_id required")
    # Validate OAuth config early to avoid generic 500s; treat 'None'/'null' as unset
    if not _is_schwab_configured():
        raise HTTPException(
            status_code=400,
            detail="Schwab OAuth not configured. Set SCHWAB_CLIENT_ID and SCHWAB_REDIRECT_URI.",
        )
    state = oauth_state_service.issue_state(user_id=user.id, account_id=req.account_id)
    connector = SchwabConnector()
    try:
        # PKCE: create verifier and derived challenge; persist verifier keyed by state
        verifier = generate_code_verifier()
        challenge = compute_code_challenge(verifier)
        save_verifier_for_state(state, verifier, ttl_seconds=600)
        # Build URL
        base_url = connector.get_authorization_url(state=state, trading=bool(req.trading))
        # Append PKCE params
        sep = "&" if "?" in base_url else "?"
        url = f"{base_url}{sep}code_challenge={urllib.parse.quote(challenge)}&code_challenge_method=S256"
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Ensure we return JSON with CORS headers instead of raw 500
        raise HTTPException(status_code=500, detail=f"schwab_link failed: {e}")
    return LinkResponse(url=url)


@router.get("/schwab/callback")
async def schwab_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    try:
        data = oauth_state_service.validate_state(state)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid state: {e}")

    uid = int(data["uid"])
    aid = int(data["aid"])

    # Locate account
    account = (
        db.query(BrokerAccount)
        .filter(BrokerAccount.id == aid, BrokerAccount.user_id == uid)
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Exchange code for tokens
    connector = SchwabConnector()
    try:
        code_verifier = pop_verifier_for_state(state)
        tokens = await connector.exchange_code_for_tokens(code, code_verifier=code_verifier)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Token exchange failed: {e}")

    # Persist encrypted credentials
    encrypted = credential_vault.encrypt_dict(tokens)
    cred = (
        db.query(AccountCredentials)
        .filter(AccountCredentials.account_id == account.id)
        .first()
    )
    token_fingerprint = hashlib.sha256(
        str(tokens.get("access_token", "")).encode("utf-8")
    ).hexdigest()
    if cred:
        cred.encrypted_credentials = encrypted
        cred.credential_hash = token_fingerprint
    else:
        cred = AccountCredentials(
            account_id=account.id,
            encrypted_credentials=encrypted,
            credential_hash=token_fingerprint,
        )
        db.add(cred)

    account.api_credentials_stored = True
    account.connection_status = "connected"
    db.commit()

    return {"status": "linked", "account_id": account.id}


