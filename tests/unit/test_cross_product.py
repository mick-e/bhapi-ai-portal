"""Unit tests for cross-product API."""


import pytest

from src.exceptions import ValidationError
from src.integrations.cross_product import (
    create_cross_product_alert,
    list_cross_product_alerts,
    register_product,
)
from tests.conftest import make_test_group


@pytest.mark.asyncio
class TestCrossProduct:
    async def test_register_product(self, test_session):
        group, _ = await make_test_group(test_session)
        reg = await register_product(
            test_session, product_name="Bhapi App", product_type="app",
            api_key_hash="abc123hash", owner_group_id=group.id,
        )
        assert reg.product_name == "Bhapi App"
        assert reg.active is True

    async def test_invalid_product_type(self, test_session):
        group, _ = await make_test_group(test_session)
        with pytest.raises(ValidationError):
            await register_product(
                test_session, product_name="T", product_type="invalid",
                api_key_hash="h", owner_group_id=group.id,
            )

    async def test_create_cross_product_alert(self, test_session):
        group, _ = await make_test_group(test_session)
        alert = await create_cross_product_alert(
            test_session, group_id=group.id, source_product="app",
            alert_type="toxicity", severity="high", title="Test Alert",
        )
        assert alert.source_product == "app"

    async def test_list_alerts(self, test_session):
        group, _ = await make_test_group(test_session)
        await create_cross_product_alert(test_session, group.id, "app", "test", "low", "Alert 1")
        await create_cross_product_alert(test_session, group.id, "portal", "test", "medium", "Alert 2")
        alerts = await list_cross_product_alerts(test_session, group.id)
        assert len(alerts) == 2
