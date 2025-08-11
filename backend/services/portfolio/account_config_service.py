"""
Account Configuration Service
============================

Service to read broker account configurations from environment variables
and populate the database with broker accounts.

This eliminates hardcoded account numbers from code and centralizes
account management.
"""

import logging
from typing import Dict, List
from datetime import datetime

from backend.config import settings
from backend.database import SessionLocal
from backend.models.broker_account import (
    BrokerAccount,
    BrokerType,
    AccountType,
    AccountStatus,
)
from backend.models.user import User, UserRole

logger = logging.getLogger(__name__)


class AccountConfigService:
    """
    Service to manage broker account configurations from environment variables.

    Reads account info from .env and ensures they exist in database.
    """

    def __init__(self):
        self.db = SessionLocal()

    def get_ibkr_accounts_from_env(self) -> List[Dict]:
        """Parse IBKR accounts from environment variables."""
        try:
            # Parse IBKR_ACCOUNTS=U19490886, U15891532
            accounts_str = settings.IBKR_ACCOUNTS
            if not accounts_str:
                logger.warning("No IBKR_ACCOUNTS found in environment")
                return []

            account_numbers = [acc.strip() for acc in accounts_str.split(",")]

            accounts = []
            for acc_num in account_numbers:
                if acc_num:
                    # Determine account type based on account number pattern
                    # This is IBKR-specific logic
                    if acc_num.startswith("U1989"):  # First account - taxable
                        account_type = AccountType.TAXABLE
                        account_name = f"IBKR Taxable ({acc_num})"
                    elif acc_num.startswith("U1589"):  # Second account - IRA
                        account_type = AccountType.IRA
                        account_name = f"IBKR Traditional IRA ({acc_num})"
                    else:
                        account_type = AccountType.TAXABLE  # Default
                        account_name = f"IBKR Account ({acc_num})"

                    accounts.append(
                        {
                            "account_number": acc_num,
                            "account_name": account_name,
                            "account_type": account_type,
                            "broker": BrokerType.IBKR,
                        }
                    )

            return accounts

        except Exception as e:
            logger.error(f"Error parsing IBKR accounts from env: {e}")
            return []

    def get_tastytrade_account_from_env(self) -> Dict:
        """Get TastyTrade account info from environment variables.
        Prefer a concrete account number from env; otherwise skip seeding.
        """
        try:
            username = getattr(settings, "TASTYTRADE_USERNAME", None)
            account_number = getattr(settings, "TASTYTRADE_ACCOUNT_NUMBER", None)
            if not username:
                logger.warning("No TASTYTRADE_USERNAME found in environment")
                return None
            if not account_number:
                # Skip seeding until we can fetch actual number from API to avoid wrong identifiers
                logger.info(
                    "TASTYTRADE_ACCOUNT_NUMBER not set; skipping TastyTrade account seeding"
                )
                return None
            return {
                "account_number": account_number,
                "account_name": f"TastyTrade ({account_number})",
                "account_type": AccountType.TAXABLE,
                "broker": BrokerType.TASTYTRADE,
            }
        except Exception as e:
            logger.error(f"Error parsing TastyTrade account from env: {e}")
            return None

    def ensure_user_exists(self, user_id: int = 1) -> User:
        """Ensure the default user exists in database."""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                user = User(
                    id=user_id,
                    username="default_user",
                    email="user@quantmatrix.com",
                    is_active=True,
                    role=UserRole.ADMIN,
                )
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)
                logger.info(f"Created default user with ID {user_id}")

            return user

        except Exception as e:
            logger.error(f"Error ensuring user exists: {e}")
            self.db.rollback()
            raise

    def seed_broker_accounts(self, user_id: int = 1) -> Dict:
        """
        Seed broker accounts from environment variables into database.

        This should be called during application startup or when adding accounts.
        """
        try:
            # Ensure user exists
            user = self.ensure_user_exists(user_id)

            results = {"created": 0, "updated": 0, "errors": 0, "accounts": []}

            # Get all account configurations
            all_accounts = []

            # IBKR accounts
            ibkr_accounts = self.get_ibkr_accounts_from_env()
            all_accounts.extend(ibkr_accounts)

            # TastyTrade account
            tt_account = self.get_tastytrade_account_from_env()
            if tt_account:
                all_accounts.append(tt_account)

            # Schwab accounts (optional, comma-separated)
            try:
                schwab_list = getattr(settings, "SCHWAB_ACCOUNTS", None)
                if schwab_list:
                    for acc in [a.strip() for a in schwab_list.split(",") if a.strip()]:
                        all_accounts.append(
                            {
                                "account_number": acc,
                                "account_name": f"Schwab Account ({acc})",
                                "account_type": AccountType.TAXABLE,
                                "broker": BrokerType.SCHWAB,
                            }
                        )
            except Exception:
                pass

            # Process each account
            for account_config in all_accounts:
                try:
                    account_number = account_config["account_number"]
                    broker = account_config["broker"]

                    # Check if account already exists
                    existing = (
                        self.db.query(BrokerAccount)
                        .filter(
                            BrokerAccount.user_id == user_id,
                            BrokerAccount.account_number == account_number,
                            BrokerAccount.broker == broker,
                        )
                        .first()
                    )

                    if existing:
                        # Update existing account
                        existing.account_name = account_config["account_name"]
                        existing.account_type = account_config["account_type"]
                        existing.updated_at = datetime.now()
                        results["updated"] += 1
                        logger.info(f"Updated existing account: {account_number}")
                    else:
                        # Create new account
                        new_account = BrokerAccount(
                            user_id=user_id,
                            broker=broker,
                            account_number=account_number,
                            account_name=account_config["account_name"],
                            account_type=account_config["account_type"],
                            status=AccountStatus.ACTIVE,
                            is_enabled=True,
                            api_credentials_stored=False,  # Will be set when credentials are added
                            currency="USD",
                            created_at=datetime.now(),
                        )
                        self.db.add(new_account)
                        results["created"] += 1
                        logger.info(f"Created new account: {account_number}")

                    results["accounts"].append(
                        {
                            "account_number": account_number,
                            "broker": broker.value,
                            "account_type": account_config["account_type"].value,
                        }
                    )

                except Exception as e:
                    logger.error(
                        f"Error processing account {account_config.get('account_number', 'UNKNOWN')}: {e}"
                    )
                    results["errors"] += 1
                    continue

            self.db.commit()

            logger.info(
                f"Account seeding completed: {results['created']} created, {results['updated']} updated, {results['errors']} errors"
            )
            return results

        except Exception as e:
            logger.error(f"Error seeding broker accounts: {e}")
            self.db.rollback()
            return {"error": str(e)}
        finally:
            self.db.close()

    def get_broker_accounts_for_user(self, user_id: int = 1) -> List[BrokerAccount]:
        """Get all broker accounts for a user."""
        try:
            accounts = (
                self.db.query(BrokerAccount)
                .filter(
                    BrokerAccount.user_id == user_id, BrokerAccount.is_enabled == True
                )
                .all()
            )

            return accounts

        except Exception as e:
            logger.error(f"Error getting broker accounts: {e}")
            return []


# Global instance
account_config_service = AccountConfigService()
