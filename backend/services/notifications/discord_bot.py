from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)


class DiscordBotClient:
    """Minimal Discord Bot API sender (no gateway connection).

    Uses HTTPS API with a bot token:
    POST /channels/{channel_id}/messages

    This is intentionally lightweight and safe for scheduled jobs.
    """

    def __init__(
        self,
        *,
        token: Optional[str] = None,
        api_base: str = "https://discord.com/api/v10",
        timeout_s: float = 10.0,
    ) -> None:
        self.token = token or getattr(settings, "DISCORD_BOT_TOKEN", None)
        self.api_base = api_base.rstrip("/")
        self.timeout_s = float(timeout_s)

    def is_configured(self) -> bool:
        return bool(self.token)

    async def send_message(
        self,
        *,
        channel_id: str,
        content: str,
        max_attempts: int = 3,
    ) -> bool:
        if not self.token:
            logger.warning("Discord bot token not configured; skipping send")
            return False
        if not channel_id:
            logger.warning("Discord channel_id missing; skipping send")
            return False

        # Discord hard limit: 2000 chars per message.
        content = (content or "").strip()
        if not content:
            return False
        chunks = [content[i : i + 1900] for i in range(0, len(content), 1900)]

        headers = {"Authorization": f"Bot {self.token}"}
        url = f"{self.api_base}/channels/{channel_id}/messages"

        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            for chunk in chunks:
                payload = {"content": chunk}
                attempt = 0
                while True:
                    attempt += 1
                    try:
                        resp = await client.post(url, headers=headers, json=payload)
                        if resp.status_code == 429:
                            # Rate limit response includes retry_after (seconds)
                            try:
                                data = resp.json()
                                retry_after = float(data.get("retry_after", 1.0))
                            except Exception:
                                retry_after = 1.0
                            if attempt >= max_attempts:
                                logger.warning("Discord rate limited; giving up after %s attempts", attempt)
                                return False
                            await asyncio.sleep(min(max(retry_after, 0.5), 10.0))
                            continue
                        resp.raise_for_status()
                        break
                    except Exception as exc:
                        if attempt >= max_attempts:
                            logger.warning("Discord bot send failed after %s attempts: %s", attempt, exc)
                            return False
                        await asyncio.sleep(0.6 * attempt)
        return True


discord_bot_client = DiscordBotClient()


