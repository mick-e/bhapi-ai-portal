"""Unit tests for web push notifications."""

from uuid import uuid4

import pytest

from src.alerts.web_push import (
    get_user_subscriptions,
    send_push_notification,
    subscribe_push,
    unsubscribe_push,
)
from src.exceptions import ValidationError
from tests.conftest import make_test_group


@pytest.mark.asyncio
class TestWebPush:
    async def test_subscribe(self, test_session):
        group, owner_id = await make_test_group(test_session)
        sub = await subscribe_push(
            test_session, user_id=owner_id, group_id=group.id,
            endpoint="https://push.example.com/abc", p256dh_key="p256dh_test", auth_key="auth_test",
        )
        assert sub.active is True
        assert sub.endpoint == "https://push.example.com/abc"

    async def test_subscribe_validation(self, test_session):
        group, owner_id = await make_test_group(test_session)
        with pytest.raises(ValidationError):
            await subscribe_push(
                test_session, user_id=owner_id, group_id=group.id,
                endpoint="", p256dh_key="", auth_key="",
            )

    async def test_unsubscribe(self, test_session):
        group, owner_id = await make_test_group(test_session)
        await subscribe_push(
            test_session, user_id=owner_id, group_id=group.id,
            endpoint="https://push.example.com/abc",
            p256dh_key="p256dh", auth_key="auth",
        )
        await unsubscribe_push(
            test_session, user_id=owner_id,
            endpoint="https://push.example.com/abc",
        )
        subs = await get_user_subscriptions(test_session, owner_id)
        assert len(subs) == 0

    async def test_list_subscriptions(self, test_session):
        group, owner_id = await make_test_group(test_session)
        await subscribe_push(
            test_session, user_id=owner_id, group_id=group.id,
            endpoint="https://push.example.com/1",
            p256dh_key="p1", auth_key="a1",
        )
        await subscribe_push(
            test_session, user_id=owner_id, group_id=group.id,
            endpoint="https://push.example.com/2",
            p256dh_key="p2", auth_key="a2",
        )
        subs = await get_user_subscriptions(test_session, owner_id)
        assert len(subs) == 2

    async def test_send_notification(self, test_session):
        group, owner_id = await make_test_group(test_session)
        await subscribe_push(
            test_session, user_id=owner_id, group_id=group.id,
            endpoint="https://push.example.com/abc",
            p256dh_key="p256dh", auth_key="auth",
        )
        sent = await send_push_notification(test_session, owner_id, "Test", "Body")
        assert sent == 1

    async def test_send_no_subscriptions(self, test_session):
        sent = await send_push_notification(test_session, uuid4(), "Test", "Body")
        assert sent == 0

    async def test_update_existing_subscription(self, test_session):
        group, owner_id = await make_test_group(test_session)
        sub1 = await subscribe_push(
            test_session, user_id=owner_id, group_id=group.id,
            endpoint="https://push.example.com/abc",
            p256dh_key="old", auth_key="old",
        )
        sub2 = await subscribe_push(
            test_session, user_id=owner_id, group_id=group.id,
            endpoint="https://push.example.com/abc",
            p256dh_key="new", auth_key="new",
        )
        assert sub2.id == sub1.id
        assert sub2.p256dh_key == "new"
