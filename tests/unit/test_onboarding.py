"""Unit tests for onboarding progress."""

from uuid import uuid4

import pytest

from src.exceptions import ValidationError
from src.portal.onboarding import (
    ONBOARDING_STEPS,
    complete_onboarding_step,
    dismiss_onboarding,
    get_onboarding_progress,
)


@pytest.mark.asyncio
class TestOnboarding:
    async def test_new_user_has_no_progress(self, test_session):
        result = await get_onboarding_progress(test_session, uuid4())
        assert result["completed_count"] == 0
        assert result["is_complete"] is False
        assert len(result["steps"]) == len(ONBOARDING_STEPS)

    async def test_complete_first_step(self, test_session):
        uid = uuid4()
        result = await complete_onboarding_step(test_session, uid, "create_group")
        assert result["completed_count"] == 1
        assert result["steps"][0]["completed"] is True

    async def test_complete_all_steps(self, test_session):
        uid = uuid4()
        for step in ONBOARDING_STEPS:
            result = await complete_onboarding_step(test_session, uid, step["key"])
        assert result["is_complete"] is True
        assert result["completed_count"] == len(ONBOARDING_STEPS)

    async def test_invalid_step_key(self, test_session):
        with pytest.raises(ValidationError):
            await complete_onboarding_step(test_session, uuid4(), "invalid_step")

    async def test_dismiss_onboarding(self, test_session):
        uid = uuid4()
        result = await dismiss_onboarding(test_session, uid)
        assert result["dismissed"] is True

    async def test_idempotent_step_completion(self, test_session):
        uid = uuid4()
        await complete_onboarding_step(test_session, uid, "create_group")
        result = await complete_onboarding_step(test_session, uid, "create_group")
        assert result["completed_count"] == 1
