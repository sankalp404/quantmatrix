from typing import List, Dict, Any


class SchwabClient:
    """Placeholder Schwab client. Replace with real OAuth and API calls."""

    def __init__(self):
        self.connected = False

    async def connect(self) -> bool:
        self.connected = True
        return True

    async def get_accounts(self) -> List[Dict[str, Any]]:
        return []

    async def get_positions(self, account_number: str) -> List[Dict[str, Any]]:
        return []

    async def get_transactions(
        self, account_number: str, days: int = 365
    ) -> List[Dict[str, Any]]:
        return []

    async def place_order(
        self, account_number: str, order: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"status": "not_implemented"}
