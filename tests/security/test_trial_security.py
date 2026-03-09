"""Security tests: trial enforcement coverage on all routers."""

import pytest

from fastapi import Depends
from src.dependencies import require_active_trial_or_subscription


def _get_router_dep_callables(router):
    """Extract dependency callables from router-level dependencies."""
    deps = []
    for dep in router.dependencies:
        if hasattr(dep, "dependency"):
            deps.append(dep.dependency)
    return deps


def _get_all_route_dep_callables(router):
    """Extract dependency callables from all route-level dependencies."""
    deps = []
    for route in router.routes:
        for dep in getattr(route, "dependencies", []):
            if hasattr(dep, "dependency"):
                deps.append(dep.dependency)
    return deps


class TestTrialEnforcementCoverage:
    """Verify the correct routers enforce trial and the correct ones are exempt."""

    @pytest.mark.parametrize("module_path", [
        "src.risk.router",
        "src.alerts.router",
        "src.reporting.router",
        "src.analytics.router",
        "src.blocking.router",
        "src.integrations.router",
    ])
    def test_protected_router_has_trial_dependency(self, module_path):
        """Each protected router should include require_active_trial_or_subscription
        at the router level."""
        import importlib
        mod = importlib.import_module(module_path)
        router = mod.router

        dep_callables = _get_router_dep_callables(router)
        assert require_active_trial_or_subscription in dep_callables, (
            f"{module_path} should enforce trial but dependency not found"
        )

    def test_capture_router_enforces_trial_per_endpoint(self):
        """Capture router uses per-endpoint trial enforcement
        (because /pair is unauthenticated)."""
        import src.capture.router as mod
        router = mod.router

        # Router-level should NOT have it (would break /pair)
        router_deps = _get_router_dep_callables(router)
        assert require_active_trial_or_subscription not in router_deps

        # But authed endpoints should have it at route level
        route_deps = _get_all_route_dep_callables(router)
        assert require_active_trial_or_subscription in route_deps, (
            "capture authed endpoints should enforce trial at route level"
        )

    def test_capture_pair_endpoint_has_no_trial_dep(self):
        """The /pair endpoint must NOT have trial enforcement."""
        import src.capture.router as mod
        router = mod.router

        pair_route = None
        for route in router.routes:
            if getattr(route, "path", "") == "/pair":
                pair_route = route
                break

        assert pair_route is not None, "/pair route not found"
        pair_deps = []
        for dep in getattr(pair_route, "dependencies", []):
            if hasattr(dep, "dependency"):
                pair_deps.append(dep.dependency)
        assert require_active_trial_or_subscription not in pair_deps

    @pytest.mark.parametrize("module_path", [
        "src.auth.router",
        "src.groups.router",
        "src.billing.router",
        "src.portal.router",
        "src.compliance.router",
    ])
    def test_exempt_router_has_no_trial_dependency(self, module_path):
        """Exempt routers (auth, groups, billing, portal, compliance)
        should NOT enforce trial to allow access when locked."""
        import importlib
        mod = importlib.import_module(module_path)
        router = mod.router

        dep_callables = _get_router_dep_callables(router)
        assert require_active_trial_or_subscription not in dep_callables, (
            f"{module_path} should be exempt from trial enforcement"
        )

    def test_trial_expired_error_returns_403(self):
        """TrialExpiredError should produce 403 with TRIAL_EXPIRED code."""
        from src.exceptions import TrialExpiredError

        err = TrialExpiredError()
        assert err.status_code == 403
        assert err.code == "TRIAL_EXPIRED"
        assert "contactus@bhapi.io" in err.message

    def test_trial_expired_custom_message(self):
        from src.exceptions import TrialExpiredError

        err = TrialExpiredError("Custom message")
        assert err.message == "Custom message"
        assert err.status_code == 403
