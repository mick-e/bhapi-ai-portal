"""Unit tests for URL content filtering."""


import pytest

from src.blocking.url_filter import (
    check_url,
    create_filter_rule,
    get_default_categories,
    list_filter_rules,
)
from src.exceptions import ValidationError
from tests.conftest import make_test_group


@pytest.mark.asyncio
class TestURLFilter:
    def test_default_categories(self):
        cats = get_default_categories()
        assert len(cats) == 10
        keys = [c["key"] for c in cats]
        assert "adult" in keys
        assert "malware" in keys

    async def test_create_rule(self, test_session):
        group, owner_id = await make_test_group(test_session)
        rule = await create_filter_rule(test_session, group.id, "adult", "block", created_by=owner_id)
        assert rule.category == "adult"
        assert rule.action == "block"

    async def test_invalid_action(self, test_session):
        group, owner_id = await make_test_group(test_session)
        with pytest.raises(ValidationError):
            await create_filter_rule(test_session, group.id, "adult", "invalid", created_by=owner_id)

    async def test_list_rules(self, test_session):
        group, owner_id = await make_test_group(test_session)
        await create_filter_rule(test_session, group.id, "adult", "block", created_by=owner_id)
        await create_filter_rule(test_session, group.id, "gambling", "warn", created_by=owner_id)
        rules = await list_filter_rules(test_session, group.id)
        assert len(rules) == 2

    async def test_check_url(self, test_session):
        group, owner_id = await make_test_group(test_session)
        await create_filter_rule(test_session, group.id, "adult", "block", created_by=owner_id)
        result = await check_url(test_session, group.id, "https://example.com")
        assert "url" in result
        assert "matching_rules" in result
