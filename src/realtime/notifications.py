"""Push notification relay for Expo push notifications."""

import structlog
import httpx
from dataclasses import dataclass

logger = structlog.get_logger()

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


@dataclass
class PushResult:
    success: bool
    ticket_id: str | None = None
    error: str | None = None


class PushNotificationRelay:
    def __init__(self):
        self._tokens: dict[str, str] = {}  # user_id -> expo_push_token

    def register_token(self, user_id: str, token: str):
        """Register an Expo push token for a user."""
        self._tokens[user_id] = token
        logger.info("push_token_registered", user_id=user_id)

    def unregister_token(self, user_id: str):
        self._tokens.pop(user_id, None)

    def get_token(self, user_id: str) -> str | None:
        return self._tokens.get(user_id)

    async def send_push(
        self,
        user_id: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> PushResult:
        """Send push notification to a user."""
        token = self._tokens.get(user_id)
        if not token:
            return PushResult(success=False, error="No push token registered")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    EXPO_PUSH_URL,
                    json={
                        "to": token,
                        "title": title,
                        "body": body,
                        "data": data or {},
                        "sound": "default",
                    },
                )
                resp.raise_for_status()
                result = resp.json()

            ticket = result.get("data", {}).get("id")
            return PushResult(success=True, ticket_id=ticket)
        except Exception as e:
            logger.error("push_send_failed", user_id=user_id, error=str(e))
            return PushResult(success=False, error=str(e))

    async def send_push_batch(
        self,
        user_ids: list[str],
        title: str,
        body: str,
        data: dict | None = None,
    ) -> list[PushResult]:
        """Send push to multiple users."""
        results = []
        for uid in user_ids:
            result = await self.send_push(uid, title, body, data)
            results.append(result)
        return results


relay = PushNotificationRelay()
