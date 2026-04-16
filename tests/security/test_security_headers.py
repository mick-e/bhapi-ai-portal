"""Security tests for CSP and HSTS headers.

Covers R-09 (Phase 4 Task 1):
- script-src must NOT include 'unsafe-inline' (XSS defense)
- HSTS must include 'preload' directive (HSTS preload list eligibility)
- Stripe domains must appear in connect-src and frame-src (billing regression-proofing)
"""

import pytest


@pytest.mark.asyncio
async def test_csp_script_src_has_no_unsafe_inline(minimal_client):
    """script-src must NOT allow 'unsafe-inline' (XSS protection)."""
    response = await minimal_client.get("/health/live")
    csp = response.headers.get("Content-Security-Policy", "")
    directives = {d.split()[0]: d for d in csp.split("; ") if d}
    script_src = directives.get("script-src", "")
    assert "'unsafe-inline'" not in script_src, (
        f"script-src still allows unsafe-inline: {script_src}"
    )


@pytest.mark.asyncio
async def test_hsts_includes_preload(minimal_client):
    """HSTS header should include 'preload' directive for HSTS preload list eligibility."""
    response = await minimal_client.get("/health/live")
    hsts = response.headers.get("Strict-Transport-Security", "")
    assert "preload" in hsts, f"HSTS missing preload: {hsts}"


@pytest.mark.asyncio
async def test_csp_includes_stripe_domains(minimal_client):
    """Stripe JS must be allowed in connect-src and frame-src for billing checkout.

    The portal uses Stripe redirect Checkout (not embedded Elements), but
    js.stripe.com is still needed for Checkout.js and fraud detection (Radar).
    This test guards against accidental removal during CSP tightening.
    """
    response = await minimal_client.get("/health/live")
    csp = response.headers.get("Content-Security-Policy", "")

    assert "https://js.stripe.com" in csp, (
        f"CSP missing js.stripe.com — billing will break: {csp}"
    )
    assert "https://api.stripe.com" in csp, (
        f"CSP missing api.stripe.com — billing will break: {csp}"
    )

    directives = {d.split()[0]: d for d in csp.split("; ") if d}
    frame_src = directives.get("frame-src", "")
    connect_src = directives.get("connect-src", "")

    assert "https://js.stripe.com" in frame_src, (
        f"frame-src missing js.stripe.com: {frame_src}"
    )
    assert "https://js.stripe.com" in connect_src, (
        f"connect-src missing js.stripe.com: {connect_src}"
    )
