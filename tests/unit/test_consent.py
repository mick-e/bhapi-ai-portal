"""Consent logic unit tests."""

import pytest
from datetime import datetime, timezone, timedelta
from src.groups.consent import calculate_age, requires_consent, get_consent_type


class TestCalculateAge:
    def test_adult(self):
        dob = datetime(1990, 6, 15, tzinfo=timezone.utc)
        age = calculate_age(dob)
        assert age >= 35

    def test_child(self):
        dob = datetime(2015, 1, 1, tzinfo=timezone.utc)
        age = calculate_age(dob)
        assert age >= 10

    def test_infant(self):
        dob = datetime(2023, 6, 1, tzinfo=timezone.utc)
        age = calculate_age(dob)
        assert age >= 2

    def test_birthday_today(self):
        now = datetime.now(timezone.utc)
        dob = datetime(now.year - 18, now.month, now.day, tzinfo=timezone.utc)
        age = calculate_age(dob)
        assert age == 18

    def test_birthday_tomorrow(self):
        now = datetime.now(timezone.utc)
        tomorrow = now + timedelta(days=1)
        dob = datetime(tomorrow.year - 18, tomorrow.month, tomorrow.day, tzinfo=timezone.utc)
        age = calculate_age(dob)
        assert age == 17

    def test_naive_datetime(self):
        """Naive datetime is handled."""
        dob = datetime(2000, 1, 1)
        age = calculate_age(dob)
        assert age >= 25


class TestRequiresConsent:
    def test_us_under_13(self):
        dob = datetime(2020, 1, 1, tzinfo=timezone.utc)
        assert requires_consent(dob, "us") is True

    def test_us_over_13(self):
        dob = datetime(2005, 1, 1, tzinfo=timezone.utc)
        assert requires_consent(dob, "us") is False

    def test_eu_under_16(self):
        dob = datetime(2015, 1, 1, tzinfo=timezone.utc)
        assert requires_consent(dob, "eu") is True

    def test_eu_over_16(self):
        dob = datetime(2005, 1, 1, tzinfo=timezone.utc)
        assert requires_consent(dob, "eu") is False

    def test_uk_under_16(self):
        dob = datetime(2015, 1, 1, tzinfo=timezone.utc)
        assert requires_consent(dob, "uk") is True

    def test_brazil_under_18(self):
        dob = datetime(2012, 1, 1, tzinfo=timezone.utc)
        assert requires_consent(dob, "br") is True

    def test_brazil_over_18(self):
        dob = datetime(2000, 1, 1, tzinfo=timezone.utc)
        assert requires_consent(dob, "br") is False

    def test_australia_under_16(self):
        dob = datetime(2015, 1, 1, tzinfo=timezone.utc)
        assert requires_consent(dob, "au") is True

    def test_no_dob(self):
        assert requires_consent(None, "us") is False

    def test_unknown_jurisdiction_defaults_16(self):
        dob = datetime(2015, 1, 1, tzinfo=timezone.utc)
        assert requires_consent(dob, "jp") is True


class TestGetConsentType:
    def test_us_coppa(self):
        dob = datetime(2020, 1, 1, tzinfo=timezone.utc)
        assert get_consent_type(dob, "us") == "coppa"

    def test_eu_gdpr(self):
        dob = datetime(2015, 1, 1, tzinfo=timezone.utc)
        assert get_consent_type(dob, "eu") == "gdpr"

    def test_uk_gdpr(self):
        dob = datetime(2015, 1, 1, tzinfo=timezone.utc)
        assert get_consent_type(dob, "uk") == "gdpr"

    def test_brazil_lgpd(self):
        dob = datetime(2012, 1, 1, tzinfo=timezone.utc)
        assert get_consent_type(dob, "br") == "lgpd"

    def test_australia(self):
        dob = datetime(2015, 1, 1, tzinfo=timezone.utc)
        assert get_consent_type(dob, "au") == "au_privacy"

    def test_adult_no_consent(self):
        dob = datetime(1990, 1, 1, tzinfo=timezone.utc)
        assert get_consent_type(dob, "us") is None

    def test_no_dob(self):
        assert get_consent_type(None, "us") is None
