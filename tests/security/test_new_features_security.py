"""Security tests for new features: billing public endpoints, school router,
literacy router, safety scores, blocking approval, SSO provisioner, and
trial enforcement on new routers."""

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app


@pytest.fixture
async def sec_client():
    """Security test client with in-memory SQLite."""
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


async def _register_family_user(client, email="family@example.com"):
    """Register a family user and return (token, headers)."""
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Test Family",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    login = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "SecurePass1",
    })
    token = login.json()["access_token"]
    return token, {"Authorization": f"Bearer {token}"}


async def _register_school_user(client, email="school@example.com"):
    """Register a school user and return (token, headers)."""
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Test School",
        "account_type": "school",
        "privacy_notice_accepted": True,
    })
    login = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "SecurePass1",
    })
    token = login.json()["access_token"]
    return token, {"Authorization": f"Bearer {token}"}


# ─── 1. Public Endpoint Access ───────────────────────────────────────────────


class TestPublicEndpoints:
    """Verify billing public endpoints are accessible without auth."""

    @pytest.mark.asyncio
    async def test_billing_plans_accessible_without_auth(self, sec_client):
        """GET /api/v1/billing/plans should return 200 without auth."""
        resp = await sec_client.get("/api/v1/billing/plans")
        assert resp.status_code == 200
        data = resp.json()
        assert "plans" in data

    @pytest.mark.asyncio
    async def test_vendor_risk_accessible_without_auth(self, sec_client):
        """GET /api/v1/billing/vendor-risk should return 200 without auth."""
        resp = await sec_client.get("/api/v1/billing/vendor-risk")
        assert resp.status_code == 200
        data = resp.json()
        assert "vendors" in data

    @pytest.mark.asyncio
    async def test_vendor_risk_specific_no_auth(self, sec_client):
        """GET /api/v1/billing/vendor-risk/{provider} should work without auth."""
        resp = await sec_client.get("/api/v1/billing/vendor-risk/openai")
        # 200 if known vendor, 404 if unknown — but not 401
        assert resp.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_billing_subscribe_requires_auth(self, sec_client):
        """POST /api/v1/billing/subscribe SHOULD require auth (not public)."""
        resp = await sec_client.post("/api/v1/billing/subscribe", json={
            "group_id": str(uuid4()),
            "plan_type": "family_monthly",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_billing_spend_requires_auth(self, sec_client):
        """GET /api/v1/billing/spend SHOULD require auth."""
        resp = await sec_client.get("/api/v1/billing/spend")
        assert resp.status_code == 401


# ─── 2. School Router Authorization ─────────────────────────────────────────


class TestSchoolRouterAuthorization:
    """Verify school endpoints require auth and enforce role checks."""

    @pytest.mark.asyncio
    async def test_school_classes_requires_auth(self, sec_client):
        """GET /api/v1/school/classes returns 401 without auth."""
        resp = await sec_client.get("/api/v1/school/classes")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_school_create_class_requires_auth(self, sec_client):
        """POST /api/v1/school/classes returns 401 without auth."""
        resp = await sec_client.post("/api/v1/school/classes", json={
            "name": "Math 101",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_school_safeguarding_requires_auth(self, sec_client):
        """GET /api/v1/school/safeguarding-report returns 401 without auth."""
        resp = await sec_client.get("/api/v1/school/safeguarding-report")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_family_user_forbidden_on_school_endpoints(self, sec_client):
        """Family users get 403 on school endpoints (wrong group type)."""
        _, headers = await _register_family_user(sec_client)
        resp = await sec_client.get("/api/v1/school/classes", headers=headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_family_user_cannot_create_class(self, sec_client):
        """Family users cannot create school classes."""
        _, headers = await _register_family_user(sec_client)
        resp = await sec_client.post("/api/v1/school/classes", json={
            "name": "Math 101",
        }, headers=headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_family_user_cannot_view_safeguarding(self, sec_client):
        """Family users cannot view safeguarding report."""
        _, headers = await _register_family_user(sec_client)
        resp = await sec_client.get(
            "/api/v1/school/safeguarding-report", headers=headers
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_invalid_token_on_school_endpoint(self, sec_client):
        """Invalid bearer token on school endpoint returns 401."""
        resp = await sec_client.get(
            "/api/v1/school/classes",
            headers={"Authorization": "Bearer fake-token"},
        )
        assert resp.status_code == 401


# ─── 3. Literacy Router Authorization ────────────────────────────────────────


class TestLiteracyRouterAuthorization:
    """Verify literacy endpoints require authentication."""

    @pytest.mark.asyncio
    async def test_literacy_modules_requires_auth(self, sec_client):
        """GET /api/v1/literacy/modules returns 401 without auth."""
        resp = await sec_client.get("/api/v1/literacy/modules")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_literacy_seed_requires_auth(self, sec_client):
        """POST /api/v1/literacy/seed returns 401 without auth."""
        resp = await sec_client.post("/api/v1/literacy/seed")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_literacy_assessments_requires_auth(self, sec_client):
        """POST /api/v1/literacy/assessments returns 401 without auth."""
        resp = await sec_client.post("/api/v1/literacy/assessments", json={
            "module_id": str(uuid4()),
            "member_id": str(uuid4()),
            "answers": [],
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_literacy_progress_requires_auth(self, sec_client):
        """GET /api/v1/literacy/progress/{member_id} returns 401 without auth."""
        resp = await sec_client.get(f"/api/v1/literacy/progress/{uuid4()}")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_literacy_invalid_token(self, sec_client):
        """Invalid token on literacy endpoint returns 401."""
        resp = await sec_client.get(
            "/api/v1/literacy/modules",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert resp.status_code == 401


# ─── 4. Safety Score Endpoints ────────────────────────────────────────────────


class TestSafetyScoreEndpoints:
    """Verify safety score endpoints require auth and validate params."""

    @pytest.mark.asyncio
    async def test_safety_score_requires_auth(self, sec_client):
        """GET /api/v1/risk/score returns 401 without auth."""
        resp = await sec_client.get(
            "/api/v1/risk/score",
            params={"member_id": str(uuid4())},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_safety_score_group_requires_auth(self, sec_client):
        """GET /api/v1/risk/score/group returns 401 without auth."""
        resp = await sec_client.get("/api/v1/risk/score/group")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_safety_score_history_requires_auth(self, sec_client):
        """GET /api/v1/risk/score/history returns 401 without auth."""
        resp = await sec_client.get(
            "/api/v1/risk/score/history",
            params={"member_id": str(uuid4())},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_safety_score_missing_member_id_returns_422(self, sec_client):
        """GET /api/v1/risk/score without member_id returns 422."""
        _, headers = await _register_family_user(sec_client, email="score@example.com")
        resp = await sec_client.get("/api/v1/risk/score", headers=headers)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_safety_score_history_missing_member_id(self, sec_client):
        """GET /api/v1/risk/score/history without member_id returns 422."""
        _, headers = await _register_family_user(sec_client, email="hist@example.com")
        resp = await sec_client.get(
            "/api/v1/risk/score/history", headers=headers
        )
        assert resp.status_code == 422


# ─── 5. Blocking Approval ────────────────────────────────────────────────────


class TestBlockingApproval:
    """Verify blocking approval endpoints require auth and validate inputs."""

    @pytest.mark.asyncio
    async def test_approval_request_requires_auth(self, sec_client):
        """POST /api/v1/blocking/approval-request returns 401 without auth."""
        resp = await sec_client.post("/api/v1/blocking/approval-request", json={
            "group_id": str(uuid4()),
            "block_rule_id": str(uuid4()),
            "member_id": str(uuid4()),
            "reason": "Please unblock",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_approve_requires_auth(self, sec_client):
        """POST /api/v1/blocking/approve/{id} returns 401 without auth."""
        resp = await sec_client.post(
            f"/api/v1/blocking/approve/{uuid4()}",
            json={"decision_note": "ok"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_deny_requires_auth(self, sec_client):
        """POST /api/v1/blocking/deny/{id} returns 401 without auth."""
        resp = await sec_client.post(
            f"/api/v1/blocking/deny/{uuid4()}",
            json={"decision_note": "no"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_pending_approvals_requires_auth(self, sec_client):
        """GET /api/v1/blocking/pending-approvals returns 401 without auth."""
        resp = await sec_client.get(
            "/api/v1/blocking/pending-approvals",
            params={"group_id": str(uuid4())},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_approve_invalid_id_returns_error(self, sec_client):
        """Approve with non-existent approval ID returns 404."""
        _, headers = await _register_family_user(sec_client, email="approve@example.com")
        resp = await sec_client.post(
            f"/api/v1/blocking/approve/{uuid4()}",
            json={"decision_note": "ok"},
            headers=headers,
        )
        # Should be 404 (not found) or 403 (trial) — not 200
        assert resp.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_deny_invalid_id_returns_error(self, sec_client):
        """Deny with non-existent approval ID returns error."""
        _, headers = await _register_family_user(sec_client, email="deny@example.com")
        resp = await sec_client.post(
            f"/api/v1/blocking/deny/{uuid4()}",
            json={"decision_note": "no"},
            headers=headers,
        )
        # Should be 404 or 403 (trial) — not 200
        assert resp.status_code in (403, 404)


# ─── 6. SSO Provisioner ──────────────────────────────────────────────────────


class TestSSOProvisioner:
    """Verify SSO auto-provisioner enforces member caps and disabled flag."""

    @pytest.mark.asyncio
    async def test_family_member_cap_enforced(self, sec_client):
        """SSO provisioner respects MAX_FAMILY_MEMBERS = 5."""
        from uuid import uuid4

        from sqlalchemy import event as sa_event
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.pool import StaticPool

        from src.constants import MAX_FAMILY_MEMBERS
        from src.database import Base
        from src.groups.models import Group, GroupMember
        from src.integrations.sso_models import SSOConfig
        from src.integrations.sso_provisioner import auto_provision_member

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @sa_event.listens_for(engine.sync_engine, "connect")
        def set_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=OFF")
            cursor.close()

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with AsyncSession(engine, expire_on_commit=False) as session:
            # Create a family group
            group_id = uuid4()
            owner_id = uuid4()
            group = Group(
                id=group_id, name="Test Family", type="family", owner_id=owner_id
            )
            session.add(group)

            # Create SSO config with auto_provision enabled
            sso_config = SSOConfig(
                id=uuid4(),
                group_id=group_id,
                provider="google_workspace",
                auto_provision_members=True,
            )
            session.add(sso_config)

            # Fill up to MAX_FAMILY_MEMBERS
            for i in range(MAX_FAMILY_MEMBERS):
                member = GroupMember(
                    id=uuid4(),
                    group_id=group_id,
                    role="member",
                    display_name=f"Member {i}",
                )
                session.add(member)

            await session.commit()

            # Try to provision one more — should return None
            result = await auto_provision_member(session, group_id, {
                "email": "extra@example.com",
                "display_name": "Extra Member",
                "external_id": "ext-999",
            })
            assert result is None, "Should not provision beyond family member cap"

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_auto_provision_disabled_returns_none(self, sec_client):
        """SSO provisioner returns None when auto_provision_members is False."""
        from uuid import uuid4

        from sqlalchemy import event as sa_event
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.pool import StaticPool

        from src.database import Base
        from src.groups.models import Group
        from src.integrations.sso_models import SSOConfig
        from src.integrations.sso_provisioner import auto_provision_member

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @sa_event.listens_for(engine.sync_engine, "connect")
        def set_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=OFF")
            cursor.close()

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with AsyncSession(engine, expire_on_commit=False) as session:
            group_id = uuid4()
            owner_id = uuid4()
            group = Group(
                id=group_id, name="Test School", type="school", owner_id=owner_id
            )
            session.add(group)

            sso_config = SSOConfig(
                id=uuid4(),
                group_id=group_id,
                provider="microsoft_entra",
                auto_provision_members=False,
            )
            session.add(sso_config)
            await session.commit()

            result = await auto_provision_member(session, group_id, {
                "email": "user@example.com",
                "display_name": "User",
                "external_id": "ext-1",
            })
            assert result is None, "Should not provision when disabled"

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_provision_no_sso_config_returns_none(self, sec_client):
        """SSO provisioner returns None when no SSOConfig exists."""
        from uuid import uuid4

        from sqlalchemy import event as sa_event
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.pool import StaticPool

        from src.database import Base
        from src.integrations.sso_provisioner import auto_provision_member

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @sa_event.listens_for(engine.sync_engine, "connect")
        def set_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=OFF")
            cursor.close()

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with AsyncSession(engine, expire_on_commit=False) as session:
            result = await auto_provision_member(session, uuid4(), {
                "email": "nobody@example.com",
                "display_name": "Nobody",
                "external_id": "ext-0",
            })
            assert result is None, "Should not provision without SSO config"

        await engine.dispose()


# ─── 7. Trial Enforcement for New Routers ─────────────────────────────────────


class TestTrialEnforcementNewRouters:
    """Verify school_router and literacy_router enforce trial/subscription."""

    def _get_router_dep_callables(self, router):
        """Extract dependency callables from router-level dependencies."""
        deps = []
        for dep in router.dependencies:
            if hasattr(dep, "dependency"):
                deps.append(dep.dependency)
        return deps

    def _get_all_route_dep_callables(self, router):
        """Extract dependency callables from all route-level dependencies."""
        deps = []
        for route in router.routes:
            for dep in getattr(route, "dependencies", []):
                if hasattr(dep, "dependency"):
                    deps.append(dep.dependency)
        return deps

    def test_literacy_router_has_trial_dependency(self):
        """Literacy router should enforce require_active_trial_or_subscription
        at the router level."""
        from src.dependencies import require_active_trial_or_subscription
        from src.literacy.router import router

        dep_callables = self._get_router_dep_callables(router)
        assert require_active_trial_or_subscription in dep_callables, (
            "literacy router should enforce trial at router level"
        )

    def test_school_router_uses_router_level_trial(self):
        """School router should enforce require_active_trial_or_subscription
        via router-level dependencies (consistent with other routers)."""
        from src.dependencies import require_active_trial_or_subscription
        from src.groups.school_router import router

        # School router uses router-level dependency (same pattern as alerts, blocking, etc.)
        dep_callables = []
        for dep in router.dependencies:
            if hasattr(dep, "dependency"):
                dep_callables.append(dep.dependency)
        assert require_active_trial_or_subscription in dep_callables, (
            "school router should enforce trial via router-level dependencies"
        )

    def test_school_router_all_endpoints_have_auth(self):
        """Every school endpoint should have get_current_user auth."""
        import inspect

        from src.auth.middleware import get_current_user
        from src.groups.school_router import router

        for route in router.routes:
            path = getattr(route, "path", "")
            endpoint = getattr(route, "endpoint", None)
            if endpoint:
                sig = inspect.signature(endpoint)
                has_auth = False
                for param in sig.parameters.values():
                    if hasattr(param.default, "dependency"):
                        if param.default.dependency is get_current_user:
                            has_auth = True
                            break
                assert has_auth, (
                    f"School endpoint {path} should have get_current_user auth"
                )
