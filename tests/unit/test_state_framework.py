"""Unit tests for the state compliance framework."""

from datetime import date

import pytest

from src.governance.state_framework import (
    StateAlreadyRegisteredError,
    StateComplianceFramework,
    StateNotRegisteredError,
)


@pytest.fixture
def framework() -> StateComplianceFramework:
    """Return a fresh framework with no pre-registered states."""
    return StateComplianceFramework(preload=False)


@pytest.fixture
def preloaded_framework() -> StateComplianceFramework:
    """Return a framework with default pre-registered states."""
    return StateComplianceFramework(preload=True)


class TestRegisterState:
    def test_register_state_regulation(self, framework: StateComplianceFramework):
        """Register a state with name, effective_date, requirements list."""
        framework.register_state(
            code="CA",
            name="California AI Transparency Act",
            effective_date=date(2027, 1, 1),
            requirements=["ai_disclosure", "risk_assessment"],
        )
        states = framework.get_registered_states()
        assert "CA" in states

    def test_register_state_stores_config(self, framework: StateComplianceFramework):
        """Registered state config is retrievable."""
        framework.register_state(
            code="TX",
            name="Texas AI Safety Act",
            effective_date=date(2027, 6, 1),
            requirements=["tool_inventory", "governance"],
        )
        config = framework.get_state_config("TX")
        assert config["name"] == "Texas AI Safety Act"
        assert config["effective_date"] == date(2027, 6, 1)
        assert "tool_inventory" in config["requirements"]

    def test_register_duplicate_state_raises(self, framework: StateComplianceFramework):
        """Registering the same state code twice raises error."""
        framework.register_state(
            code="NY",
            name="New York AI Act",
            effective_date=date(2027, 3, 1),
            requirements=["ai_usage"],
        )
        with pytest.raises(StateAlreadyRegisteredError):
            framework.register_state(
                code="NY",
                name="New York AI Act v2",
                effective_date=date(2027, 6, 1),
                requirements=["ai_usage"],
            )

    def test_register_state_normalizes_code(self, framework: StateComplianceFramework):
        """State codes are normalized to uppercase."""
        framework.register_state(
            code="ca",
            name="California",
            effective_date=date(2027, 1, 1),
            requirements=["ai_disclosure"],
        )
        assert "CA" in framework.get_registered_states()
        assert framework.get_state_config("ca") is not None

    def test_register_state_empty_code_raises(self, framework: StateComplianceFramework):
        """Empty state code raises validation error."""
        with pytest.raises(ValueError, match="state code"):
            framework.register_state(
                code="",
                name="Empty",
                effective_date=date(2027, 1, 1),
                requirements=[],
            )

    def test_register_state_empty_name_raises(self, framework: StateComplianceFramework):
        """Empty state name raises validation error."""
        with pytest.raises(ValueError, match="name"):
            framework.register_state(
                code="CA",
                name="",
                effective_date=date(2027, 1, 1),
                requirements=[],
            )


class TestGetStates:
    def test_get_registered_states_empty(self, framework: StateComplianceFramework):
        """Empty framework returns empty list."""
        assert framework.get_registered_states() == []

    def test_get_registered_states_returns_all(self, framework: StateComplianceFramework):
        """Returns all registered state codes."""
        for code, name in [("CA", "California"), ("TX", "Texas"), ("FL", "Florida")]:
            framework.register_state(
                code=code,
                name=name,
                effective_date=date(2027, 1, 1),
                requirements=["ai_usage"],
            )
        states = framework.get_registered_states()
        assert sorted(states) == ["CA", "FL", "TX"]

    def test_get_state_details(self, framework: StateComplianceFramework):
        """Get full details for a specific state."""
        framework.register_state(
            code="FL",
            name="Florida Digital Safety Act",
            effective_date=date(2027, 9, 1),
            requirements=["ai_usage", "risk_assessment", "governance"],
        )
        config = framework.get_state_config("FL")
        assert config["code"] == "FL"
        assert config["name"] == "Florida Digital Safety Act"
        assert config["effective_date"] == date(2027, 9, 1)
        assert len(config["requirements"]) == 3

    def test_get_unregistered_state_raises(self, framework: StateComplianceFramework):
        """Checking unregistered state raises error."""
        with pytest.raises(StateNotRegisteredError):
            framework.get_state_config("ZZ")


class TestCheckCompliance:
    def test_check_multi_state_compliance(self, framework: StateComplianceFramework):
        """Check compliance across multiple states simultaneously."""
        framework.register_state(
            code="OH",
            name="Ohio AI Mandate",
            effective_date=date(2026, 7, 1),
            requirements=["ai_usage", "tool_inventory"],
        )
        framework.register_state(
            code="CA",
            name="California AI Act",
            effective_date=date(2027, 1, 1),
            requirements=["ai_disclosure"],
        )

        result = framework.check_compliance(
            state_codes=["OH", "CA"],
            satisfied_requirements=["ai_usage", "tool_inventory"],
        )
        assert "OH" in result
        assert "CA" in result
        assert result["OH"]["status"] == "compliant"
        assert result["CA"]["status"] == "non_compliant"

    def test_check_compliance_partial(self, framework: StateComplianceFramework):
        """Partial compliance when some requirements met."""
        framework.register_state(
            code="TX",
            name="Texas AI Act",
            effective_date=date(2027, 6, 1),
            requirements=["ai_usage", "risk_assessment", "governance"],
        )
        result = framework.check_compliance(
            state_codes=["TX"],
            satisfied_requirements=["ai_usage"],
        )
        assert result["TX"]["status"] == "partial"
        assert result["TX"]["met"] == ["ai_usage"]
        assert sorted(result["TX"]["missing"]) == ["governance", "risk_assessment"]

    def test_check_compliance_unregistered_state_raises(
        self, framework: StateComplianceFramework
    ):
        """Checking compliance for unregistered state raises error."""
        with pytest.raises(StateNotRegisteredError):
            framework.check_compliance(
                state_codes=["ZZ"],
                satisfied_requirements=[],
            )

    def test_check_compliance_empty_states(self, framework: StateComplianceFramework):
        """Checking compliance with empty state list returns empty dict."""
        result = framework.check_compliance(state_codes=[], satisfied_requirements=[])
        assert result == {}

    def test_check_compliance_all_requirements_met(
        self, framework: StateComplianceFramework
    ):
        """All requirements met gives compliant status."""
        framework.register_state(
            code="NY",
            name="New York AI Act",
            effective_date=date(2027, 3, 1),
            requirements=["ai_usage", "governance"],
        )
        result = framework.check_compliance(
            state_codes=["NY"],
            satisfied_requirements=["ai_usage", "governance", "extra_policy"],
        )
        assert result["NY"]["status"] == "compliant"
        assert result["NY"]["missing"] == []


class TestPreloadedStates:
    def test_preloaded_has_ohio(self, preloaded_framework: StateComplianceFramework):
        """Preloaded framework includes Ohio."""
        states = preloaded_framework.get_registered_states()
        assert "OH" in states

    def test_preloaded_has_prep_states(self, preloaded_framework: StateComplianceFramework):
        """Preloaded framework includes CA, TX, FL, NY as 2027 prep."""
        states = preloaded_framework.get_registered_states()
        for code in ["CA", "TX", "FL", "NY"]:
            assert code in states, f"{code} should be pre-registered"

    def test_ohio_effective_date(self, preloaded_framework: StateComplianceFramework):
        """Ohio has Jul 1 2026 effective date."""
        config = preloaded_framework.get_state_config("OH")
        assert config["effective_date"] == date(2026, 7, 1)

    def test_prep_states_are_2027(self, preloaded_framework: StateComplianceFramework):
        """CA/TX/FL/NY have 2027 effective dates."""
        for code in ["CA", "TX", "FL", "NY"]:
            config = preloaded_framework.get_state_config(code)
            assert config["effective_date"].year == 2027, f"{code} should be 2027"

    def test_preloaded_ohio_requirements(
        self, preloaded_framework: StateComplianceFramework
    ):
        """Ohio has mandatory requirements list."""
        config = preloaded_framework.get_state_config("OH")
        assert len(config["requirements"]) > 0
        assert "ai_usage" in config["requirements"]


class TestDeadlineHelpers:
    def test_is_active_before_effective(self, framework: StateComplianceFramework):
        """State not yet active before effective date."""
        framework.register_state(
            code="CA",
            name="California",
            effective_date=date(2099, 1, 1),
            requirements=["ai_usage"],
        )
        assert framework.is_active("CA") is False

    def test_is_active_after_effective(self, framework: StateComplianceFramework):
        """State is active after effective date."""
        framework.register_state(
            code="OH",
            name="Ohio",
            effective_date=date(2020, 1, 1),
            requirements=["ai_usage"],
        )
        assert framework.is_active("OH") is True

    def test_get_upcoming_deadlines(self, preloaded_framework: StateComplianceFramework):
        """Get states with upcoming deadlines sorted by date."""
        deadlines = preloaded_framework.get_upcoming_deadlines()
        assert len(deadlines) > 0
        # Should be sorted by effective_date
        dates = [d["effective_date"] for d in deadlines]
        assert dates == sorted(dates)
