"""E2E tests for demo session endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app
from src.portal.demo import DemoSession  # noqa: F401 — register model with Base


@pytest.fixture
async def demo_client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_app()

    async def override_db():
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_demo_session(demo_client):
    res = await demo_client.post("/api/v1/portal/demo", json={
        "name": "Test User",
        "email": "test@example.com",
        "organisation": "Test School",
        "account_type": "school",
        "privacy_notice_accepted": True,
    })
    assert res.status_code == 201
    data = res.json()
    assert "demo_token" in data
    assert data["organisation"] == "Test School"


@pytest.mark.asyncio
async def test_get_demo_session(demo_client):
    create_res = await demo_client.post("/api/v1/portal/demo", json={
        "name": "Test", "email": "test@example.com",
        "organisation": "Test", "account_type": "school",
        "privacy_notice_accepted": True,
    })
    token = create_res.json()["demo_token"]
    res = await demo_client.get(f"/api/v1/portal/demo/{token}")
    assert res.status_code == 200
    assert res.json()["demo_data"] is not None


@pytest.mark.asyncio
async def test_get_nonexistent_demo(demo_client):
    res = await demo_client.get("/api/v1/portal/demo/nonexistent")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_roi_calculator(demo_client):
    res = await demo_client.get("/api/v1/portal/roi-calculator?num_students=200")
    assert res.status_code == 200
    data = res.json()
    assert data["num_students"] == 200
    assert data["annual_savings"] > 0


@pytest.mark.asyncio
async def test_roi_calculator_default_params(demo_client):
    res = await demo_client.get("/api/v1/portal/roi-calculator")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_list_case_studies(demo_client):
    res = await demo_client.get("/api/v1/portal/case-studies")
    assert res.status_code == 200
    assert len(res.json()["case_studies"]) == 3


@pytest.mark.asyncio
async def test_get_single_case_study(demo_client):
    res = await demo_client.get("/api/v1/portal/case-studies/springfield-unified")
    assert res.status_code == 200
    assert "Springfield" in res.json()["title"]


@pytest.mark.asyncio
async def test_get_nonexistent_case_study(demo_client):
    res = await demo_client.get("/api/v1/portal/case-studies/nonexistent")
    assert res.status_code == 404
