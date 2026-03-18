"""Unit tests for unified dashboard."""

import pytest
from tests.conftest import make_test_group
from src.portal.unified import get_unified_dashboard


@pytest.mark.asyncio
class TestUnifiedDashboard:
    async def test_returns_structure(self, test_session):
        group, _ = await make_test_group(test_session)
        result = await get_unified_dashboard(test_session, group.id)
        assert "dashboard" in result
        assert "cross_product_alerts" in result
        assert "products" in result

    async def test_products_section(self, test_session):
        group, _ = await make_test_group(test_session)
        result = await get_unified_dashboard(test_session, group.id)
        assert "portal" in result["products"]
        assert result["products"]["portal"]["status"] == "connected"
