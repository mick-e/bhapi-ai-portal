"""Unit tests for reward trigger logic (F14).

Tests REWARD_TRIGGERS configuration, BADGE_NAMES, and trigger evaluation logic.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.groups.rewards import (
    BADGE_NAMES,
    REWARD_TRIGGERS,
    Reward,
)


class TestRewardTriggerConfig:
    """Tests for reward trigger configuration constants."""

    def test_all_triggers_have_required_keys(self):
        """Each trigger config must have type, value, and description."""
        for name, config in REWARD_TRIGGERS.items():
            assert "type" in config, f"{name} missing 'type'"
            assert "value" in config, f"{name} missing 'value'"
            assert "description" in config, f"{name} missing 'description'"

    def test_trigger_types_are_valid(self):
        """Trigger types must be extra_time or badge."""
        valid_types = {"extra_time", "badge"}
        for name, config in REWARD_TRIGGERS.items():
            assert config["type"] in valid_types, f"{name} has invalid type: {config['type']}"

    def test_extra_time_values_are_positive(self):
        """Extra time values must be positive integers."""
        for name, config in REWARD_TRIGGERS.items():
            if config["type"] == "extra_time":
                assert config["value"] > 0, f"{name} has non-positive value: {config['value']}"
                assert isinstance(config["value"], int), f"{name} value must be int"

    def test_badge_values_are_valid_tiers(self):
        """Badge values must correspond to BADGE_NAMES keys."""
        for name, config in REWARD_TRIGGERS.items():
            if config["type"] == "badge":
                assert config["value"] in BADGE_NAMES, (
                    f"{name} has badge value {config['value']} not in BADGE_NAMES"
                )

    def test_descriptions_are_nonempty(self):
        """All descriptions must be non-empty strings."""
        for name, config in REWARD_TRIGGERS.items():
            assert len(config["description"]) > 0, f"{name} has empty description"

    def test_literacy_module_complete_trigger(self):
        """literacy_module_complete gives 15 extra minutes."""
        trigger = REWARD_TRIGGERS["literacy_module_complete"]
        assert trigger["type"] == "extra_time"
        assert trigger["value"] == 15

    def test_safety_score_above_80_trigger(self):
        """safety_score_above_80 gives 30 extra minutes."""
        trigger = REWARD_TRIGGERS["safety_score_above_80"]
        assert trigger["type"] == "extra_time"
        assert trigger["value"] == 30

    def test_week_no_high_risk_trigger(self):
        """week_no_high_risk gives a tier 1 badge."""
        trigger = REWARD_TRIGGERS["week_no_high_risk"]
        assert trigger["type"] == "badge"
        assert trigger["value"] == 1

    def test_agreement_compliance_week_trigger(self):
        """agreement_compliance_week gives 20 extra minutes."""
        trigger = REWARD_TRIGGERS["agreement_compliance_week"]
        assert trigger["type"] == "extra_time"
        assert trigger["value"] == 20


class TestBadgeNames:
    """Tests for BADGE_NAMES constant."""

    def test_badge_tiers_exist(self):
        """Tiers 1, 2, 3 must be defined."""
        assert 1 in BADGE_NAMES
        assert 2 in BADGE_NAMES
        assert 3 in BADGE_NAMES

    def test_badge_names_are_nonempty(self):
        """All badge names are non-empty strings."""
        for tier, name in BADGE_NAMES.items():
            assert isinstance(name, str)
            assert len(name) > 0

    def test_specific_badge_names(self):
        """Check specific badge names."""
        assert BADGE_NAMES[1] == "Safety Star"
        assert BADGE_NAMES[2] == "Digital Citizen"
        assert BADGE_NAMES[3] == "AI Expert"


class TestRewardModel:
    """Tests for Reward model instantiation."""

    def test_reward_table_name(self):
        """Reward model maps to 'rewards' table."""
        assert Reward.__tablename__ == "rewards"

    def test_reward_defaults(self):
        """Check default values on Reward fields."""
        now = datetime.now(timezone.utc)
        reward = Reward(
            id=uuid4(),
            group_id=uuid4(),
            member_id=uuid4(),
            reward_type="extra_time",
            trigger="literacy_module_complete",
            trigger_description="Test",
            value=15,
            earned_at=now,
            redeemed=False,
        )
        assert reward.redeemed is False
        assert reward.expires_at is None

    def test_extra_time_reward_with_expiry(self):
        """Extra time reward with expiry date."""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=30)
        reward = Reward(
            id=uuid4(),
            group_id=uuid4(),
            member_id=uuid4(),
            reward_type="extra_time",
            trigger="safety_score_above_80",
            trigger_description="Maintained safety score",
            value=30,
            earned_at=now,
            expires_at=expires,
        )
        assert reward.expires_at == expires
        assert reward.value == 30

    def test_badge_reward_no_expiry(self):
        """Badge rewards typically have no expiry."""
        now = datetime.now(timezone.utc)
        reward = Reward(
            id=uuid4(),
            group_id=uuid4(),
            member_id=uuid4(),
            reward_type="badge",
            trigger="week_no_high_risk",
            trigger_description="No high risk for a week",
            value=1,
            earned_at=now,
            expires_at=None,
        )
        assert reward.expires_at is None
        assert reward.reward_type == "badge"
