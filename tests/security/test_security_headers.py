"""Security tests for CSP and HSTS headers.

Covers R-09 (Phase 4 Task 1):
- HSTS must include 'preload' directive (HSTS preload list eligibility)
- Stripe domains must appear in connect-src and frame-src (billing regression-proofing)

Originally also enforced no 'unsafe-inline' on script-src, but Next.js App
Router (`output: "export"`) embeds inline <script>__next_f.push(...)</script>
hydration blocks that cannot be nonced (HTML built at deploy time). Removing
'unsafe-inline' caused a blank-landing-page incident on 2026-04-29.
TODO(security): replace with SHA-256 hash allowlist on follow-up branch
security/csp-script-hashes — at that point restore the strict assertion.
"""

import pytest


@pytest.mark.asyncio
async def test_csp_script_src_allows_inline_until_hash_allowlist(minimal_client):
    """Temporary: script-src must include 'unsafe-inline' for Next.js hydration.

    Strict variant (no 'unsafe-inline') is restored once SHA-256 hash allowlist
    lands. This assertion exists so a deploy that drops 'unsafe-inline' without
    landing the hash allowlist fails CI loudly instead of silently shipping a
    blank landing page.
    """
    response = await minimal_client.get("/health/live")
    csp = response.headers.get("Content-Security-Policy", "")
    directives = {d.split()[0]: d for d in csp.split("; ") if d}
    script_src = directives.get("script-src", "")
    assert "'unsafe-inline'" in script_src, (
        f"script-src missing 'unsafe-inline' — Next.js inline hydration "
        f"scripts will be blocked and the landing page will render blank. "
        f"Either restore 'unsafe-inline' or land the SHA-256 hash allowlist "
        f"(security/csp-script-hashes). Current: {script_src}"
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
