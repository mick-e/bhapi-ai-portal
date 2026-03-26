"""Literacy module security tests — auth enforcement, progress isolation, injection prevention."""

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.dependencies import require_active_trial_or_subscription
from src.groups.models import Group, GroupMember
from src.main import create_app
from src.schemas import GroupContext

GROUP_A = uuid4()
GROUP_B = uuid4()
USER_A = uuid4()
USER_B = uuid4()
MEMBER_A = uuid4()
MEMBER_B = uuid4()


def _make_auth(user_id, group_id):
    """Create a GroupContext for dependency override."""
    return GroupContext(user_id=user_id, group_id=group_id, role="admin", permissions=["*"])


async def _seed_user_group_member(session, user_id, group_id, member_id):
    """Create user, group, and member rows to satisfy FK constraints."""
    user = User(
        id=user_id,
        email=f"{user_id}@sectest.com",
        password_hash="fakehash",
        display_name="SecTest",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    session.add(user)
    await session.flush()

    group = Group(
        id=group_id,
        name="Test Group",
        type="family",
        owner_id=user_id,
    )
    session.add(group)
    await session.flush()

    member = GroupMember(
        id=member_id,
        group_id=group_id,
        user_id=user_id,
        role="parent",
        display_name="SecTest Member",
    )
    session.add(member)
    await session.flush()
    await session.commit()


@pytest.fixture
async def sec_client():
    """Security test client with no auth — for unauthenticated access tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = AsyncSession(engine, expire_on_commit=False)
    app = create_app()

    async def get_db_override():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    app.dependency_overrides[get_db] = get_db_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    await session.close()
    await engine.dispose()


@pytest.fixture
async def auth_client_a():
    """Authenticated client for user A (group A) with DB rows for FK constraints."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = AsyncSession(engine, expire_on_commit=False)

    # Create real DB rows for FK constraints
    await _seed_user_group_member(session, USER_A, GROUP_A, MEMBER_A)

    app = create_app()

    async def get_db_override():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    auth_a = _make_auth(USER_A, GROUP_A)

    async def get_user_a():
        return auth_a

    async def fake_trial_check():
        return auth_a

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = get_user_a
    app.dependency_overrides[require_active_trial_or_subscription] = fake_trial_check

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as client:
        yield client, session, app

    await session.close()
    await engine.dispose()


@pytest.fixture
async def dual_clients():
    """Two authenticated clients (user A and user B) sharing the same DB."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = AsyncSession(engine, expire_on_commit=False)

    # Create DB rows for both users/groups/members
    await _seed_user_group_member(session, USER_A, GROUP_A, MEMBER_A)
    await _seed_user_group_member(session, USER_B, GROUP_B, MEMBER_B)

    async def get_db_override():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    auth_a = _make_auth(USER_A, GROUP_A)
    auth_b = _make_auth(USER_B, GROUP_B)

    async def get_user_a():
        return auth_a

    async def get_user_b():
        return auth_b

    async def fake_trial_a():
        return auth_a

    async def fake_trial_b():
        return auth_b

    # App for user A
    app_a = create_app()
    app_a.dependency_overrides[get_db] = get_db_override
    app_a.dependency_overrides[get_current_user] = get_user_a
    app_a.dependency_overrides[require_active_trial_or_subscription] = fake_trial_a

    # App for user B
    app_b = create_app()
    app_b.dependency_overrides[get_db] = get_db_override
    app_b.dependency_overrides[get_current_user] = get_user_b
    app_b.dependency_overrides[require_active_trial_or_subscription] = fake_trial_b

    async with AsyncClient(
        transport=ASGITransport(app=app_a), base_url="http://test",
        headers={"Authorization": "Bearer test-token-a"},
    ) as client_a, AsyncClient(
        transport=ASGITransport(app=app_b), base_url="http://test",
        headers={"Authorization": "Bearer test-token-b"},
    ) as client_b:
        yield client_a, client_b, session

    await session.close()
    await engine.dispose()


# --- Authentication Required ---


@pytest.mark.asyncio
async def test_modules_requires_auth(sec_client):
    """GET /api/v1/literacy/modules requires authentication."""
    resp = await sec_client.get("/api/v1/literacy/modules")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_questions_requires_auth(sec_client):
    """GET /api/v1/literacy/modules/{id}/questions requires authentication."""
    resp = await sec_client.get(f"/api/v1/literacy/modules/{uuid4()}/questions")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_assessments_requires_auth(sec_client):
    """POST /api/v1/literacy/assessments requires authentication."""
    resp = await sec_client.post("/api/v1/literacy/assessments", json={
        "group_id": str(uuid4()),
        "member_id": str(uuid4()),
        "module_id": str(uuid4()),
        "answers": [{"question_id": str(uuid4()), "selected_answer": "A"}],
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_progress_requires_auth(sec_client):
    """GET /api/v1/literacy/progress/{member_id} requires authentication."""
    resp = await sec_client.get(f"/api/v1/literacy/progress/{uuid4()}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_seed_requires_auth(sec_client):
    """POST /api/v1/literacy/seed requires authentication."""
    resp = await sec_client.post("/api/v1/literacy/seed")
    assert resp.status_code == 401


# --- Invalid Bearer Token ---


@pytest.mark.asyncio
async def test_modules_invalid_token(sec_client):
    """Invalid bearer token returns 401 on literacy endpoints."""
    resp = await sec_client.get(
        "/api/v1/literacy/modules",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert resp.status_code == 401


# --- Input Validation ---


@pytest.mark.asyncio
async def test_invalid_module_id_format(sec_client):
    """Non-UUID module_id returns 422, not 500."""
    resp = await sec_client.get(
        "/api/v1/literacy/modules/not-a-uuid/questions",
        headers={"Authorization": "Bearer invalid"},
    )
    # Could be 401 (auth first) or 422 (validation first)
    assert resp.status_code in (401, 422)


@pytest.mark.asyncio
async def test_age_filter_validation(auth_client_a):
    """Negative age filter values are rejected."""
    client, session, app = auth_client_a
    resp = await client.get("/api/v1/literacy/modules", params={"min_age": -1})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_assessment_empty_answers_rejected(auth_client_a):
    """Assessment submission with empty answers list is rejected."""
    client, session, app = auth_client_a
    resp = await client.post("/api/v1/literacy/assessments", json={
        "group_id": str(GROUP_A),
        "member_id": str(MEMBER_A),
        "module_id": str(uuid4()),
        "answers": [],
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_assessment_nonexistent_module(auth_client_a):
    """Assessment for nonexistent module returns 404."""
    client, session, app = auth_client_a
    fake_module_id = uuid4()
    resp = await client.post("/api/v1/literacy/assessments", json={
        "group_id": str(GROUP_A),
        "member_id": str(MEMBER_A),
        "module_id": str(fake_module_id),
        "answers": [{"question_id": str(uuid4()), "selected_answer": "A"}],
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_questions_nonexistent_module(auth_client_a):
    """Questions for nonexistent module returns 404."""
    client, session, app = auth_client_a
    resp = await client.get(f"/api/v1/literacy/modules/{uuid4()}/questions")
    assert resp.status_code == 404


# --- Content Injection Prevention ---


@pytest.mark.asyncio
async def test_xss_in_assessment_answer(auth_client_a):
    """XSS payload in assessment answer is handled safely (stored as-is, not executed)."""
    client, session, app = auth_client_a

    # Seed content first
    await client.post("/api/v1/literacy/seed")

    # Get a module
    modules_resp = await client.get("/api/v1/literacy/modules")
    assert modules_resp.status_code == 200
    modules = modules_resp.json()
    assert len(modules) > 0

    module = modules[0]
    module_id = module["id"]

    # Get questions
    q_resp = await client.get(f"/api/v1/literacy/modules/{module_id}/questions")
    assert q_resp.status_code == 200
    questions = q_resp.json()
    assert len(questions) > 0

    question = questions[0]
    xss_payload = "<script>alert('xss')</script>"

    resp = await client.post("/api/v1/literacy/assessments", json={
        "group_id": str(GROUP_A),
        "member_id": str(MEMBER_A),
        "module_id": module_id,
        "answers": [{"question_id": question["id"], "selected_answer": xss_payload}],
    })
    # Should succeed (store as-is) or reject — not crash
    assert resp.status_code in (200, 422)
    if resp.status_code == 200:
        data = resp.json()
        # Verify the XSS payload is stored as plain text, not interpreted
        assert any(r["selected_answer"] == xss_payload for r in data["results"])


@pytest.mark.asyncio
async def test_sql_injection_in_assessment_answer(auth_client_a):
    """SQL injection in assessment answer does not cause server error."""
    client, session, app = auth_client_a

    await client.post("/api/v1/literacy/seed")
    modules_resp = await client.get("/api/v1/literacy/modules")
    assert modules_resp.status_code == 200
    modules = modules_resp.json()
    assert len(modules) > 0

    module = modules[0]
    q_resp = await client.get(f"/api/v1/literacy/modules/{module['id']}/questions")
    assert q_resp.status_code == 200
    questions = q_resp.json()
    assert len(questions) > 0

    question = questions[0]
    resp = await client.post("/api/v1/literacy/assessments", json={
        "group_id": str(GROUP_A),
        "member_id": str(MEMBER_A),
        "module_id": module["id"],
        "answers": [{"question_id": question["id"], "selected_answer": "'; DROP TABLE users; --"}],
    })
    assert resp.status_code != 500


# --- Questions Do Not Expose Correct Answers ---


@pytest.mark.asyncio
async def test_questions_do_not_expose_answers(auth_client_a):
    """GET questions endpoint does not include correct_answer field."""
    client, session, app = auth_client_a

    await client.post("/api/v1/literacy/seed")
    modules_resp = await client.get("/api/v1/literacy/modules")
    assert modules_resp.status_code == 200
    modules = modules_resp.json()
    assert len(modules) > 0

    module = modules[0]
    q_resp = await client.get(f"/api/v1/literacy/modules/{module['id']}/questions")
    assert q_resp.status_code == 200
    for question in q_resp.json():
        assert "correct_answer" not in question


# --- Cross-Group Progress Isolation ---


@pytest.mark.asyncio
async def test_progress_isolation_between_groups(dual_clients):
    """User A cannot see progress for a member in group B."""
    client_a, client_b, session = dual_clients

    # User A checks progress for member_b (who belongs to group B)
    # Using group_id from user A's context, which will differ from group B
    resp = await client_a.get(
        f"/api/v1/literacy/progress/{MEMBER_B}",
        params={"group_id": str(GROUP_A)},
    )
    # Should return default/empty progress (member B has no progress in group A)
    assert resp.status_code == 200
    data = resp.json()
    assert data["modules_completed"] == 0
    assert data["total_score"] == 0.0


@pytest.mark.asyncio
async def test_assessment_submitted_to_own_group(dual_clients):
    """Assessments are recorded under the submitting group context."""
    client_a, client_b, session = dual_clients

    # Seed via client A
    await client_a.post("/api/v1/literacy/seed")

    modules_resp = await client_a.get("/api/v1/literacy/modules")
    assert modules_resp.status_code == 200
    modules = modules_resp.json()
    assert len(modules) > 0

    module = modules[0]
    q_resp = await client_a.get(f"/api/v1/literacy/modules/{module['id']}/questions")
    assert q_resp.status_code == 200
    questions = q_resp.json()
    assert len(questions) > 0

    question = questions[0]

    # User A submits assessment for group A
    submit_resp = await client_a.post("/api/v1/literacy/assessments", json={
        "group_id": str(GROUP_A),
        "member_id": str(MEMBER_A),
        "module_id": module["id"],
        "answers": [{"question_id": question["id"], "selected_answer": "A"}],
    })
    assert submit_resp.status_code == 200

    # User B checks progress for member_a in group B — should be empty
    progress_resp = await client_b.get(
        f"/api/v1/literacy/progress/{MEMBER_A}",
        params={"group_id": str(GROUP_B)},
    )
    assert progress_resp.status_code == 200
    data = progress_resp.json()
    assert data["modules_completed"] == 0


# --- Score Tampering Prevention ---


@pytest.mark.asyncio
async def test_cannot_set_score_directly(auth_client_a):
    """Score field in assessment submission is ignored (server-calculated)."""
    client, session, app = auth_client_a

    await client.post("/api/v1/literacy/seed")
    modules_resp = await client.get("/api/v1/literacy/modules")
    assert modules_resp.status_code == 200
    modules = modules_resp.json()
    assert len(modules) > 0

    module = modules[0]
    q_resp = await client.get(f"/api/v1/literacy/modules/{module['id']}/questions")
    assert q_resp.status_code == 200
    questions = q_resp.json()
    assert len(questions) > 0

    question = questions[0]

    # Try to inject a score field
    resp = await client.post("/api/v1/literacy/assessments", json={
        "group_id": str(GROUP_A),
        "member_id": str(MEMBER_A),
        "module_id": module["id"],
        "answers": [{"question_id": question["id"], "selected_answer": "wrong-answer"}],
        "score": 100.0,  # Attempt to tamper
    })
    assert resp.status_code == 200
    data = resp.json()
    # Score should be server-calculated, not 100.0 (unless answer was correct)
    assert data["score"] != 100.0 or data["correct_count"] == data["total_questions"]


@pytest.mark.asyncio
async def test_cannot_modify_progress_directly(sec_client):
    """No PUT/PATCH endpoint exists for literacy progress."""
    member_id = uuid4()
    resp_put = await sec_client.put(
        f"/api/v1/literacy/progress/{member_id}",
        json={"modules_completed": 99, "total_score": 100.0, "current_level": "advanced"},
    )
    resp_patch = await sec_client.patch(
        f"/api/v1/literacy/progress/{member_id}",
        json={"total_score": 100.0},
    )
    # Either 401 (auth before route match) or 405 (no such method)
    assert resp_put.status_code in (401, 405)
    assert resp_patch.status_code in (401, 405)


# --- Pagination and Query Param Validation ---


@pytest.mark.asyncio
async def test_age_filter_non_numeric_rejected(auth_client_a):
    """Non-numeric age filter values are rejected with 422."""
    client, session, app = auth_client_a
    resp = await client.get("/api/v1/literacy/modules", params={"min_age": "abc"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_very_large_age_filter_handled(auth_client_a):
    """Very large age filter values are handled without server error."""
    client, session, app = auth_client_a
    resp = await client.get("/api/v1/literacy/modules", params={"max_age": 999999})
    assert resp.status_code == 200


# --- HTTP Method Enforcement ---


@pytest.mark.asyncio
async def test_delete_modules_not_allowed(sec_client):
    """DELETE on modules endpoint is not allowed."""
    resp = await sec_client.delete("/api/v1/literacy/modules")
    assert resp.status_code in (401, 405)


@pytest.mark.asyncio
async def test_put_modules_not_allowed(sec_client):
    """PUT on modules endpoint is not allowed."""
    resp = await sec_client.put("/api/v1/literacy/modules", json={"title": "hacked"})
    assert resp.status_code in (401, 405)
