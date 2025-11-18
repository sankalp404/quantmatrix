from __future__ import annotations

import logging
from decimal import Decimal
from typing import Dict, Any, List

from sqlalchemy.orm import Session

from backend.models.broker_account import BrokerAccount
from backend.models.position import Position, PositionType, PositionStatus
from backend.models.transaction import Transaction, TransactionType
from backend.services.clients.schwab_client import SchwabClient
from backend.services.security.credential_vault import credential_vault
from backend.models.options import Option

logger = logging.getLogger(__name__)


class SchwabSyncService:
    """
    Read-only sync for Schwab accounts (equities baseline).
    """

    def __init__(self, client: SchwabClient | None = None):
        self._client = client or SchwabClient()

    async def sync_account_comprehensive(self, account_number: str, session: Session) -> Dict:
        account: BrokerAccount | None = (
            session.query(BrokerAccount)
            .filter(BrokerAccount.account_number == str(account_number))
            .first()
        )
        if not account:
            raise ValueError(f"Schwab account {account_number} not found")

        await self._client.connect()

        # Positions
        positions = await self._client.get_positions(account_number=account_number)
        created = 0
        updated = 0
        for p in positions:
            sym = (p.get("symbol") or "").upper()
            if not sym:
                continue
            qty = Decimal(str(p.get("quantity", 0)))
            avg_cost = Decimal(str(p.get("average_cost", 0))) if p.get("average_cost") is not None else None
            total_cost = Decimal(str(p.get("total_cost_basis", 0))) if p.get("total_cost_basis") is not None else None

            existing: Position | None = (
                session.query(Position)
                .filter(Position.account_id == account.id, Position.symbol == sym)
                .first()
            )
            if existing:
                existing.quantity = qty
                existing.average_cost = avg_cost
                existing.total_cost_basis = total_cost
                existing.instrument_type = "STOCK"
                existing.position_type = PositionType.LONG if qty >= 0 else PositionType.SHORT
                existing.status = PositionStatus.OPEN if qty != 0 else PositionStatus.CLOSED
                updated += 1
            else:
                new_pos = Position(
                    user_id=account.user_id,
                    account_id=account.id,
                    symbol=sym,
                    instrument_type="STOCK",
                    position_type=PositionType.LONG if qty >= 0 else PositionType.SHORT,
                    quantity=qty,
                    status=PositionStatus.OPEN if qty != 0 else PositionStatus.CLOSED,
                    average_cost=avg_cost,
                    total_cost_basis=total_cost,
                    currency=account.currency or "USD",
                )
                session.add(new_pos)
                created += 1

        session.flush()

        # Options (if client supports it)
        options_created = 0
        options_updated = 0
        get_opts = getattr(self._client, "get_options_positions", None)
        if callable(get_opts):
            opts = await get_opts(account_number=account_number)
            for o in opts:
                und = (o.get("underlying_symbol") or "").upper()
                strike = float(o.get("strike_price", 0))
                expiry = o.get("expiry_date")  # expected as date or ISO string
                opt_type = (o.get("option_type") or "").upper()  # CALL/PUT
                open_qty = int(o.get("open_quantity", 0))
                if isinstance(expiry, str):
                    from datetime import date

                    expiry = date.fromisoformat(expiry)
                if not und or not strike or not expiry or opt_type not in ("CALL", "PUT"):
                    continue

                existing_opt: Option | None = (
                    session.query(Option)
                    .filter(
                        Option.account_id == account.id,
                        Option.underlying_symbol == und,
                        Option.strike_price == strike,
                        Option.expiry_date == expiry,
                        Option.option_type == opt_type,
                    )
                    .first()
                )
                if existing_opt:
                    existing_opt.open_quantity = open_qty
                    options_updated += 1
                else:
                    new_opt = Option(
                        user_id=account.user_id,
                        account_id=account.id,
                        symbol=o.get("symbol") or "",
                        underlying_symbol=und,
                        strike_price=strike,
                        expiry_date=expiry,
                        option_type=opt_type,
                        multiplier=float(o.get("multiplier") or 100),
                        open_quantity=open_qty,
                        currency=account.currency or "USD",
                        data_source="SCHWAB",
                    )
                    session.add(new_opt)
                    options_created += 1

        session.flush()

        # Corporate actions (basic splits/mergers handling if provided)
        get_actions = getattr(self._client, "get_corporate_actions", None)
        if callable(get_actions):
            actions = await get_actions(account_number=account_number)
            for a in actions or []:
                atype = (a.get("type") or "").lower()
                sym = (a.get("symbol") or "").upper()
                if not sym:
                    continue
                if atype == "split":
                    try:
                        num = Decimal(str(a.get("numerator") or a.get("ratio_n") or a.get("ratio_num")))
                        den = Decimal(str(a.get("denominator") or a.get("ratio_d") or a.get("ratio_den")))
                        if num <= 0 or den <= 0:
                            continue
                    except Exception:
                        continue
                    pos: Position | None = (
                        session.query(Position)
                        .filter(Position.account_id == account.id, Position.symbol == sym)
                        .first()
                    )
                    if not pos:
                        continue
                    # Adjust quantity and average cost
                    q = Decimal(pos.quantity or 0)
                    ac = Decimal(pos.average_cost or 0)
                    if q != 0 and ac > 0:
                        pos.quantity = q * num / den
                        pos.average_cost = ac * den / num
                        session.flush()

        return {
            "status": "success",
            "positions_created": created,
            "positions_updated": updated,
            "options_created": options_created,
            "options_updated": options_updated,
        }


