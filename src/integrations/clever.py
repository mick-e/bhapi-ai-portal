"""Clever API client — OAuth2 + roster sync."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()

CLEVER_API_BASE = "https://api.clever.com/v3.0"


async def fetch_clever_roster(access_token: str) -> list[dict]:
    """Fetch student/teacher roster from Clever API."""
    import httpx

    headers = {"Authorization": f"Bearer {access_token}"}
    students = []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{CLEVER_API_BASE}/users", headers=headers, params={"role": "student"})
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("data", []):
                    user = item.get("data", {})
                    students.append({
                        "sis_id": item.get("id", ""),
                        "first_name": user.get("name", {}).get("first", ""),
                        "last_name": user.get("name", {}).get("last", ""),
                        "email": user.get("email", ""),
                        "role": "member",
                    })
            elif resp.status_code == 401:
                logger.error("clever_auth_failed")
                raise ValueError("Invalid Clever access token")
    except ValueError:
        raise
    except Exception as exc:
        logger.error("clever_fetch_error", error=str(exc))

    logger.info("clever_roster_fetched", count=len(students))
    return students
