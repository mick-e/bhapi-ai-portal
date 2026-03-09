"""Canvas LMS roster sync adapter."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()

CANVAS_DEFAULT_BASE = "https://canvas.instructure.com"


async def fetch_canvas_roster(
    access_token: str,
    base_url: str = CANVAS_DEFAULT_BASE,
    course_id: str = "",
) -> list[dict]:
    """Fetch student roster from Canvas LMS API.

    Canvas REST API: GET /api/v1/courses/{course_id}/enrollments
    If no course_id, fetches all users from the account.
    """
    import httpx

    students: list[dict] = []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }

            if course_id:
                url: str | None = f"{base_url}/api/v1/courses/{course_id}/enrollments"
                params: dict = {
                    "type[]": "StudentEnrollment",
                    "per_page": 100,
                    "state[]": "active",
                }
            else:
                url = f"{base_url}/api/v1/accounts/self/users"
                params = {"per_page": 100}

            while url:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code == 200:
                    items = resp.json()
                    for item in items:
                        user = item.get("user", item)
                        sortable = user.get("sortable_name", "")
                        name = user.get("name", "")

                        if "," in sortable:
                            last_name = sortable.split(",")[0].strip()
                            first_name = sortable.split(",")[-1].strip()
                        elif name:
                            parts = name.split()
                            first_name = parts[0] if parts else ""
                            last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
                        else:
                            first_name = ""
                            last_name = ""

                        students.append({
                            "sis_id": str(
                                user.get("sis_user_id", user.get("id", ""))
                            ),
                            "first_name": first_name,
                            "last_name": last_name,
                            "email": user.get("login_id", user.get("email", "")),
                            "role": "member",
                        })

                    # Canvas uses Link header for pagination
                    link_header = resp.headers.get("Link", "")
                    url = None
                    params = {}  # Clear params for subsequent pages
                    for part in link_header.split(","):
                        if 'rel="next"' in part:
                            url = part.split(";")[0].strip().strip("<>")
                            break
                elif resp.status_code == 401:
                    raise ValueError("Invalid Canvas access token")
                else:
                    raise ValueError(f"Canvas API error: {resp.status_code}")
    except ValueError:
        raise
    except Exception as exc:
        logger.error("canvas_fetch_error", error=str(exc))

    logger.info("canvas_roster_fetched", count=len(students))
    return students
