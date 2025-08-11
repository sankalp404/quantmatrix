#!/usr/bin/env python3
"""
Clean IBKR Client - Real-time Trading API
Focuses on real-time positions, trading, and market data via ib_insync.
Historical data and tax lots handled by separate FlexQuery client.
"""

import asyncio
import logging
import time
import random
from typing import Dict, List

try:
    from ib_insync import IB, util, Contract, Stock, Option

    IBKR_AVAILABLE = True
except ImportError:
    IBKR_AVAILABLE = False
    IB = None

try:
    from backend.config import settings
except ImportError:
    from config import settings

logger = logging.getLogger(__name__)


class IBKRClient:
    """
    Clean IBKR client for real-time trading operations.

    Responsibilities:
    - Real-time positions and account data
    - Order placement and management
    - Live market data
    - Connection management (SINGLETON)

    NOT responsible for:
    - Historical statements (use FlexQuery)
    - Tax lot calculations (use FlexQuery)
    - CSV parsing (use FlexQuery)
    """

    _instance = None
    _lock = asyncio.Lock() if IBKR_AVAILABLE else None

    def __new__(cls):
        """Singleton to prevent multiple connections."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        self._initialized = True

        if not IBKR_AVAILABLE:
            logger.error("❌ ib_insync not available")
            self.ib = None
            return

        self.ib = IB()
        self.connected = False
        self.client_id = None
        self.managed_accounts = []

    async def connect(self) -> bool:
        """Connect to IBKR Gateway/TWS with proper singleton management."""
        if not IBKR_AVAILABLE:
            return False

        async with self._lock:
            # Check existing connection
            if self.connected and self.ib.isConnected():
                logger.info("✅ Already connected to IBKR")
                return True

            # Clean up any existing connection
            await self._cleanup()

            try:
                logger.info("🔄 Connecting to IBKR Gateway...")

                # Generate unique client ID
                self.client_id = self._generate_client_id()

                # Connect with timeout
                await asyncio.wait_for(
                    self.ib.connectAsync(
                        host=getattr(settings, "IBKR_HOST", "127.0.0.1"),
                        port=getattr(settings, "IBKR_PORT", 7497),
                        clientId=self.client_id,
                        timeout=20,
                    ),
                    timeout=25,
                )

                # Verify connection
                await asyncio.sleep(1)
                self.managed_accounts = self.ib.managedAccounts()

                if self.managed_accounts:
                    self.connected = True
                    logger.info(f"✅ Connected to IBKR (Client ID: {self.client_id})")
                    logger.info(f"📊 Accounts: {self.managed_accounts}")
                    return True
                else:
                    raise Exception("No managed accounts found")

            except Exception as e:
                logger.error(f"❌ Connection failed: {e}")
                await self._cleanup()
            return False

    def _generate_client_id(self) -> int:
        """Generate unique client ID to avoid conflicts."""
        base_id = getattr(settings, "IBKR_CLIENT_ID", 1)
        timestamp = int(time.time()) % 1000
        random_part = random.randint(1, 99)

        # Keep within IBKR range (0-32767)
        client_id = (base_id * 1000 + timestamp + random_part) % 32767
        return max(1, client_id)

    async def _cleanup(self):
        """Clean up existing connection."""
        try:
            if self.ib and self.ib.isConnected():
                logger.info("🧹 Cleaning up IBKR connection...")
                self.ib.disconnect()
                await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")
        finally:
            self.connected = False
            self.client_id = None
            self.managed_accounts = []

    async def get_positions(self, account_id: str) -> List[Dict]:
        """Get current positions for account."""
        if not await self._ensure_connected():
            return []

        try:
            positions = self.ib.positions(account_id)

            position_data = []
            for pos in positions:
                if pos.position != 0:  # Only non-zero positions
                    position_data.append(
                        {
                            "account": pos.account,
                            "symbol": pos.contract.symbol,
                            "position": float(pos.position),
                            "market_value": (
                                float(pos.marketValue) if pos.marketValue else 0.0
                            ),
                            "avg_cost": float(pos.avgCost) if pos.avgCost else 0.0,
                            "unrealized_pnl": (
                                float(pos.unrealizedPNL) if pos.unrealizedPNL else 0.0
                            ),
                            "contract_type": pos.contract.secType,
                            "currency": pos.contract.currency or "USD",
                            "exchange": pos.contract.exchange,
                        }
                    )

            logger.info(f"📊 Retrieved {len(position_data)} positions for {account_id}")
            return position_data

        except Exception as e:
            logger.error(f"❌ Error getting positions: {e}")
            return []

    async def get_account_summary(self, account_id: str) -> Dict:
        """Get account summary data."""
        if not await self._ensure_connected():
            return {}

        try:
            summary = self.ib.accountSummary(account_id)

            summary_data = {}
            for item in summary:
                summary_data[item.tag] = {
                    "value": item.value,
                    "currency": item.currency,
                }

            logger.info(f"📊 Retrieved account summary for {account_id}")
            return summary_data

        except Exception as e:
            logger.error(f"❌ Error getting account summary: {e}")
            return {}

    async def _ensure_connected(self) -> bool:
        """Ensure we have a valid connection."""
        if not self.connected or not self.ib.isConnected():
            logger.warning("🔄 Connection lost - reconnecting...")
            return await self.connect()
        return True

    def get_status(self) -> Dict:
        """Get connection status."""
        return {
            "connected": self.connected,
            "client_id": self.client_id,
            "accounts": self.managed_accounts,
            "gateway_clients": (
                len(self.managed_accounts) if self.managed_accounts else 0
            ),
        }

    async def disconnect(self):
        """Properly disconnect."""
        await self._cleanup()
        logger.info("✅ IBKR disconnected")


# Global singleton instance
ibkr_client = IBKRClient()
