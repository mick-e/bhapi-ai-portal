"""ClassLink OneRoster API client — OAuth2 + roster sync."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()

CLASSLINK_API_BASE = "https://nodeapi.classlink.com/v2"


async def fetch_classlink_roster(access_token: str) -> list[dict]:
    """Fetch student roster from ClassLink OneRoster API."""
    import httpx

    headers = {"Authorization": f"Bearer {access_token}"}
    students = []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{CLASSLINK_API_BASE}/users", headers=headers, params={"role": "student"})
            if resp.status_code == 200:
                data = resp.json()
                for user in data.get("users", []):
                    students.append({
                        "sis_id": user.get("sourcedId", ""),
                        "first_name": user.get("givenName", ""),
                        "last_name": user.get("familyName", ""),
                        "email": user.get("email", ""),
                        "role": "member",
                    })
            elif resp.status_code == 401:
                raise ValueError("Invalid ClassLink access token")
    except ValueError:
        raise
    except Exception as exc:
        logger.error("classlink_fetch_error", error=str(exc))

    logger.info("classlink_roster_fetched", count=len(students))
    return students
