"""
TastyTrade Client
Production-grade TastyTrade integration for comprehensive transaction and tax lot data
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

try:
    from tastytrade import Session, Account, DXLinkStreamer
    from tastytrade.account import CurrentPosition, Transaction
    from tastytrade.instruments import get_option_chain, Equity, Option
    from tastytrade.dxfeed import Quote, Greeks, Trade
    from tastytrade.order import NewOrder, OrderAction, OrderTimeInForce, OrderType

    TASTYTRADE_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("tastytrade SDK not available - TastyTrade integration disabled")
    TASTYTRADE_AVAILABLE = False

from backend.config import settings

logger = logging.getLogger(__name__)


class TastyTradeClient:
    """
    Production-grade TastyTrade client implementing best practices:
    - Robust connection management
    - Comprehensive transaction history
    - Tax lot calculation from positions
    - Error handling and retry logic
    - Consistent data format with other brokerages
    """

    _instance = None
    _connection_lock = asyncio.Lock() if TASTYTRADE_AVAILABLE else None

    def __new__(cls):
        """Singleton pattern to enforce single connection."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self.session = None
            self.accounts = []
            self.connected = False
            self.connection_start_time = None
            self.retry_count = 0
            self.max_retries = 3
            self.base_retry_delay = 2  # seconds

            # Connection tracking
            self.connection_health = {
                "status": "disconnected",
                "last_successful_request": None,
                "consecutive_failures": 0,
                "connection_uptime": 0,
            }
            self._initialized = True

    async def connect_with_retry(self, max_attempts: int = 3) -> bool:
        """Connect to TastyTrade with retry logic and health monitoring."""
        if not TASTYTRADE_AVAILABLE:
            return False

        if not self._connection_lock:
            return False

        async with self._connection_lock:
            for attempt in range(max_attempts):
                try:
                    logger.info(
                        f"🔄 TastyTrade connection attempt {attempt + 1}/{max_attempts}"
                    )

                    # Use configured environment
                    is_test_env = getattr(settings, "TASTYTRADE_IS_TEST", True)
                    username = getattr(settings, "TASTYTRADE_USERNAME", None)
                    password = getattr(settings, "TASTYTRADE_PASSWORD", None)

                    if not username or not password:
                        logger.error("TastyTrade credentials not configured")
                        return False

                    # Create session
                    self.session = Session(username, password, is_test=is_test_env)

                    # Test connection by getting accounts
                    self.accounts = Account.get(self.session)

                    if not self.accounts:
                        raise Exception("No TastyTrade accounts found")

                    self.connected = True
                    self.connection_start_time = datetime.now()
                    self.retry_count = 0

                    # Update health status
                    self.connection_health.update(
                        {
                            "status": "connected",
                            "last_successful_request": datetime.now(),
                            "consecutive_failures": 0,
                            "connection_uptime": 0,
                        }
                    )

                    # Verify connection with basic request
                    await self._verify_connection()

                    logger.info(
                        f"✅ Successfully connected to TastyTrade {'TEST' if is_test_env else 'PRODUCTION'}"
                    )
                    logger.info(f"📊 Found {len(self.accounts)} TastyTrade accounts")

                    return True

                except Exception as e:
                    logger.error(
                        f"❌ TastyTrade connection attempt {attempt + 1} failed: {e}"
                    )
                    self.connected = False

                    if attempt < max_attempts - 1:
                        wait_time = self.base_retry_delay * (2**attempt)
                        logger.info(f"⏳ Waiting {wait_time}s before retry...")
                        await asyncio.sleep(wait_time)

            logger.error(
                f"❌ Failed to connect to TastyTrade after {max_attempts} attempts"
            )
            return False

    async def _verify_connection(self) -> bool:
        """Verify connection health with a simple API call."""
        try:
            if not self.accounts:
                return False

            # Test with account balance request
            account = self.accounts[0]
            balances = account.get_balances(self.session)

            self.connection_health.update(
                {"last_successful_request": datetime.now(), "consecutive_failures": 0}
            )

            logger.info("✅ Verification: TastyTrade connection healthy")
            return True

        except Exception as e:
            logger.warning(f"⚠️ Verification: TastyTrade connection issue: {e}")
            self.connection_health["consecutive_failures"] += 1
            return False

    async def disconnect(self):
        """Disconnect from TastyTrade with proper cleanup."""
        try:
            if self.session:
                # No explicit disconnect needed for TastyTrade sessions
                self.session = None

            self.connected = False
            self.connection_start_time = None
            self.accounts = []

            # Update health status
            self.connection_health["status"] = "disconnected"

            logger.info("📴 TastyTrade disconnected")

        except Exception as e:
            logger.warning(f"Error during TastyTrade disconnect: {e}")

    async def get_accounts(self) -> List[Dict[str, Any]]:
        """Get list of TastyTrade accounts."""
        try:
            if not self.connected or not self.accounts:
                logger.warning("Not connected to TastyTrade")
                return []

            accounts_data = []
            for account in self.accounts:
                account_data = {
                    "account_number": account.account_number,
                    "nickname": getattr(account, "nickname", ""),
                    "account_type": getattr(account, "account_type_name", "Unknown"),
                    "is_closed": getattr(account, "is_closed", False),
                    "is_firm_error": getattr(account, "is_firm_error", False),
                    "is_firm_proprietary": getattr(
                        account, "is_firm_proprietary", False
                    ),
                    "is_futures_approved": getattr(
                        account, "is_futures_approved", False
                    ),
                    "is_test_drive": getattr(account, "is_test_drive", False),
                }
                accounts_data.append(account_data)

            logger.info(f"✅ Retrieved {len(accounts_data)} TastyTrade accounts")
            return accounts_data

        except Exception as e:
            logger.error(f"❌ Error getting TastyTrade accounts: {e}")
            return []

    async def get_current_positions(
        self, account_number: str = None
    ) -> List[Dict[str, Any]]:
        """Get current positions for a TastyTrade account."""
        try:
            if not self.connected:
                logger.warning("Not connected to TastyTrade")
                return []

            # Safe conversion helpers
            def safe_float(value, default=0.0):
                """Safely convert value to float, handling None and other edge cases."""
                if value is None:
                    return default
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return default

            def safe_str(value, default="Unknown"):
                """Safely convert value to string, handling None."""
                if value is None:
                    return default
                return str(value)

            def safe_bool(value, default=False):
                """Safely convert value to bool, handling None."""
                if value is None:
                    return default
                return bool(value)

            # Find the account
            target_account = None
            if account_number:
                for account in self.accounts:
                    if account.account_number == account_number:
                        target_account = account
                        break
            else:
                target_account = self.accounts[0] if self.accounts else None

            if not target_account:
                logger.warning(f"Account {account_number} not found")
                return []

            # Get positions using TastyTrade SDK - use the correct method
            positions = target_account.get_positions(self.session)

            positions_data = []
            for position in positions:
                try:
                    position_data = {
                        "symbol": position.symbol,
                        "instrument_type": position.instrument_type,
                        "quantity": safe_float(position.quantity),
                        "quantity_direction": safe_str(
                            getattr(position, "quantity_direction", None)
                        ),
                        "close_price": safe_float(
                            getattr(position, "close_price", None)
                        ),
                        "average_open_price": safe_float(
                            getattr(position, "average_open_price", None)
                        ),
                        "average_yearly_market_close_price": safe_float(
                            getattr(position, "average_yearly_market_close_price", None)
                        ),
                        "average_daily_market_close_price": safe_float(
                            getattr(position, "average_daily_market_close_price", None)
                        ),
                        "multiplier": safe_float(
                            getattr(position, "multiplier", None), 1.0
                        ),
                        "cost_effect": safe_str(getattr(position, "cost_effect", None)),
                        "is_suppressed": safe_bool(
                            getattr(position, "is_suppressed", None)
                        ),
                        "is_frozen": safe_bool(getattr(position, "is_frozen", None)),
                        "realized_day_gain": safe_float(
                            getattr(position, "realized_day_gain", None)
                        ),
                        "realized_day_gain_effect": safe_str(
                            getattr(position, "realized_day_gain_effect", None), "None"
                        ),
                        "realized_day_gain_date": getattr(
                            position, "realized_day_gain_date", None
                        ),
                        "realized_today": safe_float(
                            getattr(position, "realized_today", None)
                        ),
                        "created_at": getattr(position, "created_at", None),
                        "updated_at": getattr(position, "updated_at", None),
                        "mark": safe_float(getattr(position, "mark", None)),
                        "mark_value": safe_float(getattr(position, "mark_value", None)),
                        "restricted_quantity": safe_float(
                            getattr(position, "restricted_quantity", None)
                        ),
                        "expired_quantity": safe_float(
                            getattr(position, "expired_quantity", None)
                        ),
                        "expiring_quantity": safe_float(
                            getattr(position, "expiring_quantity", None)
                        ),
                        "right_quantity": safe_float(
                            getattr(position, "right_quantity", None)
                        ),
                        "pending_quantity": safe_float(
                            getattr(position, "pending_quantity", None)
                        ),
                        "account_number": target_account.account_number,
                    }

                    # Add instrument-specific data
                    if hasattr(position, "instrument"):
                        instrument = position.instrument
                        position_data.update(
                            {
                                "underlying_symbol": getattr(
                                    instrument, "underlying_symbol", ""
                                ),
                                "product_code": getattr(instrument, "product_code", ""),
                                "exchange": getattr(instrument, "exchange", ""),
                                "listed_market": getattr(
                                    instrument, "listed_market", ""
                                ),
                                "description": getattr(instrument, "description", ""),
                                "is_closing_only": getattr(
                                    instrument, "is_closing_only", False
                                ),
                                "active": getattr(instrument, "active", True),
                            }
                        )

                        # Options-specific data
                        if position.instrument_type in [
                            "Equity Option",
                            "Index Option",
                        ]:
                            position_data.update(
                                {
                                    "option_type": getattr(
                                        instrument, "option_type", ""
                                    ),
                                    "strike_price": float(
                                        getattr(instrument, "strike_price", 0)
                                    ),
                                    "expiration_date": getattr(
                                        instrument, "expiration_date", None
                                    ),
                                    "days_to_expiration": getattr(
                                        instrument, "days_to_expiration", 0
                                    ),
                                    "delta": (
                                        float(getattr(instrument, "delta", 0))
                                        if hasattr(instrument, "delta")
                                        else None
                                    ),
                                    "gamma": (
                                        float(getattr(instrument, "gamma", 0))
                                        if hasattr(instrument, "gamma")
                                        else None
                                    ),
                                    "theta": (
                                        float(getattr(instrument, "theta", 0))
                                        if hasattr(instrument, "theta")
                                        else None
                                    ),
                                    "vega": (
                                        float(getattr(instrument, "vega", 0))
                                        if hasattr(instrument, "vega")
                                        else None
                                    ),
                                }
                            )

                    positions_data.append(position_data)

                except Exception as e:
                    logger.error(f"Error processing position {position.symbol}: {e}")
                    continue

            logger.info(
                f"✅ Retrieved {len(positions_data)} TastyTrade positions for {target_account.account_number}"
            )
            return positions_data

        except Exception as e:
            logger.error(f"❌ Error getting TastyTrade positions: {e}")
            import traceback

            traceback.print_exc()
            return []

    async def get_trade_history(
        self, account_number: str, days: int = 365
    ) -> List[Dict[str, Any]]:
        """Return filled trades as dictionaries expected by sync service."""
        if not TASTYTRADE_AVAILABLE:
            return []
        try:
            account = next(
                (a for a in self.accounts if a.account_number == account_number), None
            )
            if not account:
                return []
            start = datetime.utcnow() - timedelta(days=days)
            end = datetime.utcnow()
            txns = account.get_history(
                self.session, start_date=start.date(), end_date=end.date()
            )

            results: List[Dict[str, Any]] = []
            for t in txns:
                try:
                    if getattr(t, "transaction_type", "") != "Trade":
                        continue
                    transformed = self._transform_tastytrade_transaction(
                        t, account_number
                    )
                    if not transformed:
                        continue
                    executed_iso = (
                        f"{transformed.get('date')}T{transformed.get('time')}"
                    )
                    results.append(
                        {
                            "symbol": transformed.get("symbol", ""),
                            "side": transformed.get("action", ""),
                            "quantity": float(transformed.get("quantity", 0) or 0),
                            "price": float(transformed.get("price", 0) or 0),
                            "order_id": str(transformed.get("order_id", "") or ""),
                            "execution_id": str(
                                transformed.get("execution_id", "") or ""
                            ),
                            "executed_at": executed_iso,
                        }
                    )
                except Exception:
                    continue

            return results
        except Exception as e:
            logger.error(f"TT trade history error: {e}")
            return []

    async def get_transactions(
        self, account_number: str, days: int = 365
    ) -> List[Dict[str, Any]]:
        if not TASTYTRADE_AVAILABLE:
            return []
        try:
            account = next(
                (a for a in self.accounts if a.account_number == account_number), None
            )
            if not account:
                return []
            start = datetime.utcnow() - timedelta(days=days)
            end = datetime.utcnow()
            txns = account.get_history(
                self.session, start_date=start.date(), end_date=end.date()
            )
            return [
                self._transform_tastytrade_transaction(t, account_number) for t in txns
            ]
        except Exception as e:
            logger.error(f"TT transactions error: {e}")
            return []

    async def get_dividends(
        self, account_number: str, days: int = 365
    ) -> List[Dict[str, Any]]:
        if not TASTYTRADE_AVAILABLE:
            return []
        try:
            account = next(
                (a for a in self.accounts if a.account_number == account_number), None
            )
            if not account:
                return []
            start = datetime.utcnow() - timedelta(days=days)
            end = datetime.utcnow()
            txns = account.get_history(
                self.session, start_date=start.date(), end_date=end.date()
            )
            return [
                self._transform_tastytrade_transaction(t, account_number)
                for t in txns
                if getattr(t, "transaction_type", "") in ["Dividend", "Cash Dividend"]
            ]
        except Exception as e:
            logger.error(f"TT dividends error: {e}")
            return []

    async def get_account_balances(self, account_number: str) -> Dict[str, Any]:
        if not TASTYTRADE_AVAILABLE:
            return {}
        try:
            account = next(
                (a for a in self.accounts if a.account_number == account_number), None
            )
            if not account:
                return {}
            bal = account.get_balances(self.session)
            return {
                "cash_balance": float(getattr(bal, "cash_balance", 0) or 0),
                "net_liquidating_value": float(
                    getattr(bal, "net_liquidating_value", 0) or 0
                ),
                "long_margin_value": float(getattr(bal, "long_margin_value", 0) or 0),
                "short_margin_value": float(getattr(bal, "short_margin_value", 0) or 0),
            }
        except Exception as e:
            logger.error(f"TT balance error: {e}")
            return {}

    async def get_enhanced_account_statements(
        self, account_number: str, days: int = 365
    ) -> List[Dict[str, Any]]:
        """
        Get comprehensive transaction history from TastyTrade.
        Returns standardized transaction format consistent with IBKR.
        """
        if not self.connected:
            logger.warning("TastyTrade not connected for transaction retrieval")
            return []

        try:
            logger.info(
                f"📊 Fetching enhanced TastyTrade statements for account {account_number} ({days} days)"
            )

            # Find the account
            account = next(
                (acc for acc in self.accounts if acc.account_number == account_number),
                None,
            )
            if not account:
                logger.error(f"Account {account_number} not found in TastyTrade")
                return []

            # Get transaction history using TastyTrade API
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Use the correct TastyTrade API to get transactions
            try:
                logger.info(
                    f"Fetching transactions from {start_date.date()} to {end_date.date()}"
                )
                transactions = await account.a_get_history(
                    session=self.session,
                    start_date=start_date.date(),
                    end_date=end_date.date(),
                    per_page=250,  # Get more transactions per request
                )

                # First pass: collect all raw transactions for correlation
                raw_transactions = list(transactions)

                all_transactions = []
                for txn in raw_transactions:
                    # Transform to standardized format with context of all transactions
                    transaction = self._transform_tastytrade_transaction(
                        txn, account_number, raw_transactions
                    )
                    if transaction:
                        all_transactions.append(transaction)

            except Exception as e:
                logger.error(f"Error fetching TastyTrade transactions: {e}")
                all_transactions = []

            # Sort by datetime descending
            all_transactions.sort(
                key=lambda x: f"{x['date']} {x['time']}", reverse=True
            )

            logger.info(
                f"✅ Enhanced TastyTrade statements: {len(all_transactions)} transactions for {account_number}"
            )
            return all_transactions

        except Exception as e:
            logger.error(f"❌ Error getting TastyTrade enhanced statements: {e}")
            return []

    def _transform_tastytrade_transaction(
        self, txn: Any, account_number: str, all_transactions: List[Any] = None
    ) -> Optional[Dict[str, Any]]:
        """Transform TastyTrade transaction to standardized format with enhanced descriptions."""
        try:
            # Extract basic transaction data with safe None handling
            executed_at = getattr(txn, "executed_at", None) or getattr(
                txn, "transaction_date", None
            )
            if not executed_at:
                return None

            # Determine transaction type and action with safe None handling
            action = getattr(txn, "action", "") or ""
            transaction_type = (
                "BUY" if ("Buy" in action or "Deposit" in action) else "SELL"
            )

            # Get instrument details with safe None handling
            instrument = getattr(txn, "instrument", None)
            symbol = getattr(instrument, "symbol", "CASH") if instrument else "CASH"
            instrument_type = (
                getattr(instrument, "instrument_type", "CASH") if instrument else "CASH"
            )

            # Financial details with safe None handling and defaults
            quantity = float(getattr(txn, "quantity", 0) or 0)
            price = float(getattr(txn, "price", 0) or 0)
            value = float(getattr(txn, "value", 0) or 0)
            commission = float(getattr(txn, "commission", 0) or 0)
            fees = float(getattr(txn, "regulatory_fees", 0) or 0)
            net_value = float(getattr(txn, "net_value", value) or value)

            # Settlement details with safe None handling
            clearing_date = getattr(txn, "clearing_date", None)
            settlement_date = (
                clearing_date.strftime("%Y-%m-%d") if clearing_date else None
            )

            # Transaction ID with safe None handling
            txn_id = (
                getattr(txn, "id", "")
                or f"tt_{account_number}_{executed_at.timestamp()}"
            )
            order_id = str(getattr(txn, "order_id", "") or "")

            # ENHANCED DESCRIPTION LOGIC WITH CORRELATION
            if symbol == "CASH":
                # For CASH transactions, try to correlate with nearby option transactions
                related_option = None

                if all_transactions and executed_at:
                    # Look for option transactions within 5 minutes of this CASH transaction
                    time_window = timedelta(minutes=5)

                    for other_txn in all_transactions:
                        try:
                            other_executed_at = getattr(
                                other_txn, "executed_at", None
                            ) or getattr(other_txn, "transaction_date", None)
                            if not other_executed_at:
                                continue

                            # Check if within time window
                            if (
                                abs((executed_at - other_executed_at).total_seconds())
                                <= time_window.total_seconds()
                            ):
                                other_instrument = getattr(
                                    other_txn, "instrument", None
                                )
                                if other_instrument:
                                    other_symbol = getattr(
                                        other_instrument, "symbol", ""
                                    )
                                    other_instrument_type = getattr(
                                        other_instrument, "instrument_type", ""
                                    )

                                    # Found a related option transaction
                                    if (
                                        other_symbol != "CASH"
                                        and "Option" in other_instrument_type
                                    ):
                                        related_option = {
                                            "symbol": other_symbol,
                                            "instrument_type": other_instrument_type,
                                            "strike": getattr(
                                                other_instrument, "strike_price", ""
                                            ),
                                            "option_type": getattr(
                                                other_instrument, "option_type", ""
                                            ),
                                            "expiration": getattr(
                                                other_instrument, "expiration_date", ""
                                            ),
                                            "action": getattr(other_txn, "action", ""),
                                        }
                                        break
                        except Exception:
                            continue

                # Generate enhanced description based on correlation
                if related_option:
                    option_desc = f"{related_option['symbol']}"
                    if related_option["option_type"] and related_option["strike"]:
                        option_desc += f" {related_option['option_type'].upper()} ${related_option['strike']}"
                    if related_option["expiration"]:
                        try:
                            exp_str = (
                                related_option["expiration"].strftime("%m/%d/%y")
                                if hasattr(related_option["expiration"], "strftime")
                                else str(related_option["expiration"])
                            )
                            option_desc += f" exp {exp_str}"
                        except:
                            pass

                    if "SELL_TO_CLOSE" in action or "CLOSE" in action:
                        description = f"CASH Settlement: {option_desc} closed for ${abs(value):.2f}"
                    elif "SELL_TO_OPEN" in action or "OPEN" in action:
                        description = (
                            f"CASH Credit: {option_desc} sold for ${abs(value):.2f}"
                        )
                    elif "Assignment" in action:
                        description = f"CASH Assignment: {option_desc} assigned for ${abs(value):.2f}"
                    elif "Exercise" in action:
                        description = f"CASH Exercise: {option_desc} exercised for ${abs(value):.2f}"
                    elif "Expiration" in action:
                        description = f"CASH Expiration: {option_desc} expired for ${abs(value):.2f}"
                    else:
                        description = f"CASH Settlement: {option_desc} - {action} ${abs(value):.2f}"
                else:
                    # No related option found, use generic CASH description
                    if "SELL_TO_CLOSE" in action:
                        description = (
                            f"CASH Settlement: Option closed for ${abs(value):.2f}"
                        )
                    elif "SELL_TO_OPEN" in action:
                        description = f"CASH Credit: Option sold for ${abs(value):.2f}"
                    elif "BUY_TO_CLOSE" in action:
                        description = f"CASH Debit: Option closed for ${abs(value):.2f}"
                    elif "BUY_TO_OPEN" in action:
                        description = (
                            f"CASH Debit: Option purchased for ${abs(value):.2f}"
                        )
                    elif "Assignment" in action:
                        description = (
                            f"CASH Assignment: Option assigned for ${abs(value):.2f}"
                        )
                    elif "Exercise" in action:
                        description = (
                            f"CASH Exercise: Option exercised for ${abs(value):.2f}"
                        )
                    elif "Expiration" in action:
                        description = (
                            f"CASH Expiration: Option expired for ${abs(value):.2f}"
                        )
                    else:
                        # Fall back to enhanced generic description
                        description = f"CASH Transaction: {action} ${abs(value):.2f}"
            else:
                # For non-CASH transactions, use standard format
                if instrument_type in ["Equity Option", "Future Option", "Option"]:
                    # For options, include strike and expiration if available
                    strike = getattr(instrument, "strike_price", "")
                    exp_date = getattr(instrument, "expiration_date", "")
                    option_type = getattr(instrument, "option_type", "")

                    if strike and exp_date and option_type:
                        description = f"{symbol} {option_type.upper()} ${strike} exp {exp_date.strftime('%m/%d/%y') if hasattr(exp_date, 'strftime') else exp_date} - {action}"
                    else:
                        description = f"{symbol} Option - {action}"
                else:
                    # For stocks and other instruments
                    description = f"{symbol} {action}"

            transaction = {
                "id": f"tt_{txn_id}",
                "order_id": order_id,
                "account": account_number,
                "symbol": symbol,
                "description": description,  # Enhanced description
                "type": "TRADE",
                "action": transaction_type,
                "quantity": abs(quantity),
                "price": price,
                "amount": abs(value),
                "commission": commission,
                "currency": "USD",
                "exchange": "TASTYTRADE",
                "date": executed_at.strftime("%Y-%m-%d"),
                "time": executed_at.strftime("%H:%M:%S"),
                "settlement_date": settlement_date,
                "source": "tastytrade_enhanced",
                "contract_type": str(instrument_type),
                "execution_id": str(txn_id),
                "net_amount": net_value,
            }

            return transaction

        except Exception as e:
            logger.warning(f"Error transforming TastyTrade transaction: {e}")
            return None

    async def get_enhanced_tax_lots(self, account_number: str) -> List[Dict[str, Any]]:
        """
        Get tax lots from TastyTrade positions with comprehensive P&L calculations.
        Returns standardized tax lot format consistent with IBKR.
        """
        if not self.connected:
            logger.warning("TastyTrade not connected for tax lot retrieval")
            return []

        try:
            logger.info(
                f"📊 Fetching enhanced TastyTrade tax lots for account {account_number}"
            )

            # Find the account
            account = next(
                (acc for acc in self.accounts if acc.account_number == account_number),
                None,
            )
            if not account:
                logger.error(f"Account {account_number} not found in TastyTrade")
                return []

            # Get current positions
            positions = account.get_positions(self.session)
            logger.info(
                f"📈 Found {len(positions)} TastyTrade positions for tax lot calculation"
            )

            tax_lots = []

            for position in positions:
                try:
                    # Only process positions with actual holdings
                    if float(position.quantity) == 0:
                        continue

                    # Get transaction history to build tax lots
                    symbol = position.symbol

                    # For TastyTrade, each position represents one tax lot
                    # (TastyTrade uses FIFO by default and shows aggregated positions)

                    # Calculate tax lot details
                    quantity = float(position.quantity)
                    cost_per_share = float(position.average_open_price)
                    current_price = (
                        float(position.close_price)
                        if position.close_price
                        else cost_per_share
                    )

                    # Handle options multiplier
                    multiplier = getattr(position, "multiplier", 1)
                    if position.instrument_type.value in [
                        "Equity Option",
                        "Future Option",
                    ]:
                        multiplier = 100  # Standard option multiplier

                    cost_basis = abs(quantity) * cost_per_share * multiplier
                    current_value = abs(quantity) * current_price * multiplier
                    unrealized_pnl = current_value - cost_basis
                    unrealized_pnl_pct = (
                        (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0
                    )

                    # Estimate acquisition date (TastyTrade doesn't provide exact date per lot)
                    # Use position creation date or estimate from recent transactions
                    acquisition_date = getattr(position, "created_at", datetime.now())
                    if hasattr(acquisition_date, "strftime"):
                        acquisition_date_str = acquisition_date.strftime("%Y-%m-%d")
                    else:
                        acquisition_date_str = datetime.now().strftime("%Y-%m-%d")

                    # Calculate days held
                    try:
                        acq_date = datetime.strptime(acquisition_date_str, "%Y-%m-%d")
                        days_held = (datetime.now() - acq_date).days
                    except:
                        days_held = 0

                    tax_lot = {
                        "lot_id": f"enhanced_tt_{position.symbol}_{account_number}",
                        "account_id": account_number,
                        "symbol": position.symbol,
                        "acquisition_date": acquisition_date_str,
                        "quantity": abs(quantity),
                        "cost_per_share": cost_per_share,
                        "current_price": current_price,
                        "cost_basis": cost_basis,
                        "current_value": current_value,
                        "unrealized_pnl": unrealized_pnl,
                        "unrealized_pnl_pct": unrealized_pnl_pct,
                        "days_held": days_held,
                        "is_long_term": days_held >= 365,
                        "contract_type": position.instrument_type.value,
                        "currency": "USD",
                        "execution_id": f"tt_pos_{position.symbol}",
                        "source": "tastytrade_enhanced",
                        "multiplier": multiplier,
                    }

                    tax_lots.append(tax_lot)

                except Exception as e:
                    logger.warning(
                        f"Error processing TastyTrade position {position.symbol}: {e}"
                    )
                    continue

            logger.info(
                f"✅ Enhanced TastyTrade tax lots: {len(tax_lots)} lots for {account_number}"
            )
            return tax_lots

        except Exception as e:
            logger.error(f"❌ Error getting TastyTrade enhanced tax lots: {e}")
            return []

    async def get_account_info(self, account_number: str) -> Dict[str, Any]:
        """Get comprehensive account information from TastyTrade."""
        if not self.connected:
            await self.connect_with_retry()

        try:
            account = next(
                (acc for acc in self.accounts if acc.account_number == account_number),
                None,
            )
            if not account:
                return {"error": f"Account {account_number} not found"}

            # Get account balances
            balances = account.get_balances(self.session)

            # Get positions for metrics
            positions = account.get_positions(self.session)

            return {
                "account_number": account_number,
                "account_type": "Individual",  # TastyTrade default
                "broker": "TASTYTRADE",
                "net_liquidating_value": float(balances.net_liquidating_value),
                "total_cash": float(balances.total_cash),
                "buying_power": float(balances.buying_power),
                "day_trading_buying_power": float(balances.day_trading_buying_power),
                "positions_count": len(positions),
                "maintenance_requirement": float(balances.maintenance_requirement),
                "margin_equity": float(balances.margin_equity),
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting TastyTrade account info: {e}")
            return {"error": str(e)}


# Global instance
tastytrade_client = TastyTradeClient()
