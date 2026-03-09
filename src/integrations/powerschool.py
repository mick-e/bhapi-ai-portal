"""PowerSchool SIS roster sync adapter."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()

POWERSCHOOL_DEFAULT_BASE = "https://powerschool.example.com"


async def fetch_powerschool_roster(
    access_token: str, base_url: str = POWERSCHOOL_DEFAULT_BASE
) -> list[dict]:
    """Fetch student roster from PowerSchool API.

    PowerSchool REST API: GET /ws/v1/district/student
    Returns students with sis_id, first_name, last_name, email, role.
    """
    import httpx

    students: list[dict] = []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }
            resp = await client.get(
                f"{base_url}/ws/v1/district/student",
                headers=headers,
                params={"expansions": "emails,demographics", "pagesize": 1000},
            )
            if resp.status_code == 200:
                data = resp.json()
                raw_students = data.get("students", {}).get("student", [])
                if isinstance(raw_students, dict):
                    raw_students = [raw_students]  # Single result wrapped in dict

                for s in raw_students:
                    email = ""
                    emails = s.get("emails", {}).get("email", [])
                    if isinstance(emails, dict):
                        emails = [emails]
                    if emails:
                        email = emails[0].get("emailAddress", "")

                    students.append({
                        "sis_id": str(s.get("id", "")),
                        "first_name": s.get("name", {}).get("first_name", ""),
                        "last_name": s.get("name", {}).get("last_name", ""),
                        "email": email,
                        "role": "member",
                    })
            elif resp.status_code == 401:
                logger.error("powerschool_auth_failed")
                raise ValueError("Invalid PowerSchool access token")
            else:
                raise ValueError(f"PowerSchool API error: {resp.status_code}")
    except ValueError:
        raise
    except Exception as exc:
        logger.error("powerschool_fetch_error", error=str(exc))

    logger.info("powerschool_roster_fetched", count=len(students))
    return students
