"""Unit tests for district management."""

import pytest
from uuid import uuid4
from tests.conftest import make_test_group
from src.groups.district import (
    create_district, add_school_to_district,
    get_district, list_district_schools, get_district_summary,
)
from src.exceptions import NotFoundError, ConflictError


@pytest.mark.asyncio
class TestDistrict:
    async def test_create_district(self, test_session):
        d = await create_district(test_session, name="Test District", admin_email="admin@example.com")
        assert d.name == "Test District"
        assert d.active is True

    async def test_create_with_duplicate_code(self, test_session):
        await create_district(test_session, name="A", admin_email="a@example.com", code="D01")
        with pytest.raises(ConflictError):
            await create_district(test_session, name="B", admin_email="b@example.com", code="D01")

    async def test_add_school(self, test_session):
        d = await create_district(test_session, name="District", admin_email="d@example.com")
        group, _ = await make_test_group(test_session, group_type="school")
        school = await add_school_to_district(test_session, d.id, group.id, "Test School", 100)
        assert school.pilot_status == "pilot"
        assert school.student_count == 100

    async def test_add_school_nonexistent_district(self, test_session):
        group, _ = await make_test_group(test_session, group_type="school")
        with pytest.raises(NotFoundError):
            await add_school_to_district(test_session, uuid4(), group.id, "School")

    async def test_district_summary(self, test_session):
        d = await create_district(test_session, name="District", admin_email="d@example.com")
        group, _ = await make_test_group(test_session, group_type="school")
        await add_school_to_district(test_session, d.id, group.id, "School 1", 50)
        summary = await get_district_summary(test_session, d.id)
        assert summary["total_schools"] == 1
        assert summary["total_students"] == 50
