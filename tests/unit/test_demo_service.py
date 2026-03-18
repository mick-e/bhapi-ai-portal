"""Unit tests for demo session service."""

import pytest

from src.portal.demo import (
    create_demo_session,
    get_demo_session,
    list_demo_sessions,
    calculate_roi,
    get_case_studies,
    get_case_study,
    DemoSession,
)
from src.exceptions import NotFoundError, ValidationError


@pytest.mark.asyncio
class TestCreateDemoSession:
    async def test_creates_demo_with_token(self, test_session):
        session = await create_demo_session(
            test_session, name="Test", email="test@example.com",
            organisation="Test School", account_type="school",
        )
        assert session.demo_token.startswith("demo_")
        assert session.organisation == "Test School"
        assert session.active is True
        assert session.views == 0

    async def test_rejects_invalid_account_type(self, test_session):
        with pytest.raises(ValidationError):
            await create_demo_session(
                test_session, name="Test", email="test@example.com",
                organisation="Test", account_type="invalid",
            )

    async def test_school_demo_has_school_data(self, test_session):
        session = await create_demo_session(
            test_session, name="Test", email="test@example.com",
            organisation="Test", account_type="school",
        )
        assert "school" in session.demo_data

    async def test_enterprise_demo_no_school_data(self, test_session):
        session = await create_demo_session(
            test_session, name="Test", email="test@example.com",
            organisation="Test", account_type="enterprise",
        )
        assert "school" not in session.demo_data


@pytest.mark.asyncio
class TestGetDemoSession:
    async def test_get_valid_session(self, test_session):
        created = await create_demo_session(
            test_session, name="Test", email="test@example.com",
            organisation="Test", account_type="school",
        )
        retrieved = await get_demo_session(test_session, created.demo_token)
        assert retrieved.id == created.id
        assert retrieved.views == 1  # incremented

    async def test_get_nonexistent_token(self, test_session):
        with pytest.raises(NotFoundError):
            await get_demo_session(test_session, "nonexistent")


@pytest.mark.asyncio
class TestListDemoSessions:
    async def test_list_returns_created(self, test_session):
        await create_demo_session(
            test_session, name="A", email="a@example.com",
            organisation="Org A", account_type="school",
        )
        sessions = await list_demo_sessions(test_session)
        assert len(sessions) >= 1


class TestROICalculator:
    def test_basic_calculation(self):
        result = calculate_roi(num_students=100)
        assert result["num_students"] == 100
        assert result["annual_savings"] > 0
        assert result["roi_percentage"] > 0

    def test_higher_students_higher_bhapi_cost(self):
        r100 = calculate_roi(num_students=100)
        r500 = calculate_roi(num_students=500)
        assert r500["bhapi_monthly_cost"] > r100["bhapi_monthly_cost"]

    def test_zero_incidents_lower_savings(self):
        r_normal = calculate_roi(num_students=100, avg_incidents_per_month=5)
        r_zero = calculate_roi(num_students=100, avg_incidents_per_month=0)
        assert r_normal["annual_savings"] > r_zero["annual_savings"]

    def test_result_has_all_fields(self):
        result = calculate_roi(num_students=100)
        assert "monthly_savings" in result
        assert "annual_savings" in result
        assert "roi_percentage" in result
        assert "payback_months" in result
        assert "incident_reduction_pct" in result


class TestCaseStudies:
    def test_get_all_case_studies(self):
        studies = get_case_studies()
        assert len(studies) == 3

    def test_get_by_id(self):
        study = get_case_study("springfield-unified")
        assert study is not None
        assert study["title"] == "Springfield Unified School District"

    def test_get_nonexistent_returns_none(self):
        assert get_case_study("nonexistent") is None

    def test_each_study_has_results(self):
        for study in get_case_studies():
            assert len(study["results"]) > 0
            assert "quote" in study
            assert "quote_author" in study
