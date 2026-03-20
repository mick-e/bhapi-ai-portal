"""Unit tests for the age tier permission engine."""

import uuid
from datetime import date, datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.age_tier.rules import (
    AgeTier,
    TIER_PERMISSIONS,
    age_from_dob,
    check_permission,
    get_permissions,
    get_tier_for_age,
)


# ---------------------------------------------------------------------------
# age_from_dob tests
# ---------------------------------------------------------------------------


class TestAgeFromDob:
    """Test age calculation from date of birth."""

    def test_age_from_date(self):
        """Calculate age from a plain date."""
        # Someone born 10 years ago today
        today = datetime.now(timezone.utc).date()
        dob = today.replace(year=today.year - 10)
        assert age_from_dob(dob) == 10

    def test_age_from_datetime(self):
        """Calculate age from a datetime."""
        today = datetime.now(timezone.utc).date()
        dob = datetime(today.year - 8, today.month, today.day, tzinfo=timezone.utc)
        assert age_from_dob(dob) == 8

    def test_birthday_not_yet_this_year(self):
        """Age decremented if birthday hasn't happened yet."""
        today = datetime.now(timezone.utc).date()
        # Born 12 years ago but birthday is tomorrow
        if today.month == 12 and today.day == 31:
            # Edge case: use Jan 1 of next year concept — just shift by day
            future_month, future_day = 1, 1
            dob = date(today.year - 12 + 1, future_month, future_day)
        else:
            # Add one day to month/day to push birthday into the future
            from calendar import monthrange
            max_day = monthrange(today.year, today.month)[1]
            if today.day < max_day:
                dob = date(today.year - 12, today.month, today.day + 1)
            elif today.month < 12:
                dob = date(today.year - 12, today.month + 1, 1)
            else:
                dob = date(today.year - 11, 1, 1)
        assert age_from_dob(dob) == 11

    def test_birthday_today(self):
        """Exact birthday — age increments."""
        today = datetime.now(timezone.utc).date()
        dob = today.replace(year=today.year - 7)
        assert age_from_dob(dob) == 7

    def test_leap_year_birthday(self):
        """Feb 29 birthday in a non-leap year."""
        # Someone born on Feb 29, 2012
        dob = date(2012, 2, 29)
        age = age_from_dob(dob)
        # Age should be reasonable (14 in 2026)
        today = datetime.now(timezone.utc).date()
        expected = today.year - 2012
        if (today.month, today.day) < (2, 29):
            expected -= 1
        assert age == expected

    def test_newborn(self):
        """A baby born today is age 0."""
        today = datetime.now(timezone.utc).date()
        assert age_from_dob(today) == 0

    def test_very_young_child(self):
        """A 1-year-old."""
        today = datetime.now(timezone.utc).date()
        dob = today.replace(year=today.year - 1)
        assert age_from_dob(dob) == 1


# ---------------------------------------------------------------------------
# get_tier_for_age tests
# ---------------------------------------------------------------------------


class TestGetTierForAge:
    """Test tier assignment from age."""

    def test_age_4_no_tier(self):
        assert get_tier_for_age(4) is None

    def test_age_5_young(self):
        assert get_tier_for_age(5) == AgeTier.YOUNG

    def test_age_7_young(self):
        assert get_tier_for_age(7) == AgeTier.YOUNG

    def test_age_9_young(self):
        assert get_tier_for_age(9) == AgeTier.YOUNG

    def test_age_10_preteen(self):
        assert get_tier_for_age(10) == AgeTier.PRETEEN

    def test_age_11_preteen(self):
        assert get_tier_for_age(11) == AgeTier.PRETEEN

    def test_age_12_preteen(self):
        assert get_tier_for_age(12) == AgeTier.PRETEEN

    def test_age_13_teen(self):
        assert get_tier_for_age(13) == AgeTier.TEEN

    def test_age_14_teen(self):
        assert get_tier_for_age(14) == AgeTier.TEEN

    def test_age_15_teen(self):
        assert get_tier_for_age(15) == AgeTier.TEEN

    def test_age_16_no_tier(self):
        assert get_tier_for_age(16) is None

    def test_age_0_no_tier(self):
        assert get_tier_for_age(0) is None

    def test_negative_age_no_tier(self):
        assert get_tier_for_age(-1) is None


# ---------------------------------------------------------------------------
# get_permissions tests
# ---------------------------------------------------------------------------


class TestGetPermissions:
    """Test permission retrieval and overrides."""

    def test_young_base_permissions(self):
        perms = get_permissions(AgeTier.YOUNG)
        assert perms["can_post"] is True
        assert perms["can_message"] is False
        assert perms["can_upload_video"] is False
        assert perms["moderation_mode"] == "pre_publish"
        assert perms["max_contacts"] == 5
        assert perms["max_post_length"] == 200
        assert perms["max_daily_posts"] == 5

    def test_preteen_base_permissions(self):
        perms = get_permissions(AgeTier.PRETEEN)
        assert perms["can_message"] is True
        assert perms["can_upload_video"] is False
        assert perms["can_add_contacts"] is True
        assert perms["max_contacts"] == 20
        assert perms["max_daily_posts"] == 15

    def test_teen_base_permissions(self):
        perms = get_permissions(AgeTier.TEEN)
        assert perms["can_upload_video"] is True
        assert perms["can_use_ai_chat"] is True
        assert perms["moderation_mode"] == "post_publish"
        assert perms["max_contacts"] == 50
        assert perms["max_daily_posts"] == 30

    def test_all_tiers_have_18_permissions(self):
        for tier in AgeTier:
            perms = get_permissions(tier)
            assert len(perms) == 18, f"{tier} has {len(perms)} permissions, expected 18"

    def test_feature_override_grants_permission(self):
        """Parent grants messaging to a young child."""
        perms = get_permissions(AgeTier.YOUNG, feature_overrides={"can_message": True})
        assert perms["can_message"] is True

    def test_feature_override_restricts_permission(self):
        """Parent restricts posting for a teen."""
        perms = get_permissions(AgeTier.TEEN, feature_overrides={"can_post": False})
        assert perms["can_post"] is False

    def test_feature_override_numeric(self):
        """Parent reduces max contacts."""
        perms = get_permissions(AgeTier.TEEN, feature_overrides={"max_contacts": 10})
        assert perms["max_contacts"] == 10

    def test_unknown_override_ignored(self):
        """Override for unknown permission is silently ignored."""
        perms = get_permissions(AgeTier.YOUNG, feature_overrides={"can_fly": True})
        assert "can_fly" not in perms

    def test_locked_features_bool(self):
        """Locked boolean feature becomes False."""
        perms = get_permissions(AgeTier.TEEN, locked_features=["can_message"])
        assert perms["can_message"] is False

    def test_locked_features_numeric(self):
        """Locked numeric feature becomes 0."""
        perms = get_permissions(AgeTier.TEEN, locked_features=["max_contacts"])
        assert perms["max_contacts"] == 0

    def test_locked_features_string(self):
        """Locked string feature becomes 'disabled'."""
        perms = get_permissions(AgeTier.TEEN, locked_features=["moderation_mode"])
        assert perms["moderation_mode"] == "disabled"

    def test_locked_overrides_override(self):
        """Locked features take precedence over overrides."""
        perms = get_permissions(
            AgeTier.YOUNG,
            feature_overrides={"can_message": True},
            locked_features=["can_message"],
        )
        assert perms["can_message"] is False

    def test_no_location_sharing_any_tier(self):
        """Location sharing disabled by default for all tiers."""
        for tier in AgeTier:
            perms = get_permissions(tier)
            assert perms["can_share_location"] is False

    def test_permissions_are_copies(self):
        """Ensure returned permissions don't modify the base matrix."""
        perms = get_permissions(AgeTier.YOUNG, feature_overrides={"can_post": False})
        base = TIER_PERMISSIONS[AgeTier.YOUNG]
        assert base["can_post"] is True  # Original unchanged


# ---------------------------------------------------------------------------
# check_permission tests
# ---------------------------------------------------------------------------


class TestCheckPermission:
    """Test single permission checks."""

    def test_check_bool_true(self):
        assert check_permission(AgeTier.TEEN, "can_post") is True

    def test_check_bool_false(self):
        assert check_permission(AgeTier.YOUNG, "can_message") is False

    def test_check_numeric_positive(self):
        assert check_permission(AgeTier.PRETEEN, "max_contacts") is True

    def test_check_numeric_zero(self):
        assert check_permission(AgeTier.YOUNG, "max_message_length") is False

    def test_check_string_active(self):
        assert check_permission(AgeTier.TEEN, "moderation_mode") is True

    def test_check_string_disabled(self):
        assert check_permission(
            AgeTier.TEEN, "moderation_mode", locked_features=["moderation_mode"]
        ) is False

    def test_check_unknown_permission(self):
        assert check_permission(AgeTier.TEEN, "nonexistent") is False

    def test_check_with_override(self):
        assert check_permission(
            AgeTier.YOUNG, "can_message", feature_overrides={"can_message": True}
        ) is True

    def test_check_override_then_lock(self):
        """Lock wins over override."""
        assert check_permission(
            AgeTier.YOUNG,
            "can_message",
            feature_overrides={"can_message": True},
            locked_features=["can_message"],
        ) is False


# ---------------------------------------------------------------------------
# AgeTier enum tests
# ---------------------------------------------------------------------------


class TestAgeTierEnum:
    """Test AgeTier enum behavior."""

    def test_str_values(self):
        assert str(AgeTier.YOUNG) == "young"
        assert str(AgeTier.PRETEEN) == "preteen"
        assert str(AgeTier.TEEN) == "teen"

    def test_from_string(self):
        assert AgeTier("young") == AgeTier.YOUNG
        assert AgeTier("preteen") == AgeTier.PRETEEN
        assert AgeTier("teen") == AgeTier.TEEN

    def test_invalid_value(self):
        with pytest.raises(ValueError):
            AgeTier("adult")

    def test_all_tiers_in_matrix(self):
        for tier in AgeTier:
            assert tier in TIER_PERMISSIONS
