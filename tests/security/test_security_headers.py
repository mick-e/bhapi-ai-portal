"""Security tests for CSP and HSTS headers.

Covers R-09 (Phase 4 Task 1):
- script-src must NOT include 'unsafe-inline' (XSS defense)
- HSTS must include 'preload' directive (HSTS preload list eligibility)
- Stripe domains must appear in connect-src and frame-src (billing regression-proofing)
- When the Next.js static export is built, its inline-script SHA-256 hashes
  appear in script-src so hydration is not blocked. (Incident 2026-04-29:
  removing 'unsafe-inline' without a hash substitute caused a blank landing
  page. The hash allowlist closes that gap without reopening the XSS surface.)
"""

import base64
import hashlib
from pathlib import Path

import pytest

from src.main import _extract_inline_script_hashes


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
async def test_csp_script_src_includes_hash_allowlist_when_built(minimal_client):
    """When portal/out is present, its inline-script hashes appear in script-src.

    Skipped if the static export hasn't been built — CI may run tests before
    `npm run build`. The hotfix-regression assertion above still protects
    the live deploy because Render builds portal/out as part of the Docker
    image, so production always has a populated allowlist.
    """
    portal_dir = Path(__file__).resolve().parents[2] / "portal" / "out"
    if not portal_dir.is_dir() or not list(portal_dir.glob("*.html")):
        pytest.skip("portal/out not built — hash allowlist test needs static export")

    response = await minimal_client.get("/health/live")
    csp = response.headers.get("Content-Security-Policy", "")
    directives = {d.split()[0]: d for d in csp.split("; ") if d}
    script_src = directives.get("script-src", "")
    assert "'sha256-" in script_src, (
        f"script-src missing SHA-256 hash allowlist — Next.js inline "
        f"hydration scripts will be blocked. Did the static export build "
        f"correctly? Current: {script_src}"
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


# ---------------------------------------------------------------------------
# Inline-script hash collector — pure function tests
# ---------------------------------------------------------------------------


def test_extract_inline_script_hashes_picks_inline_only(tmp_path):
    """Inline <script> tags hashed; <script src=...> tags skipped."""
    (tmp_path / "page.html").write_text(
        "<html><body>"
        '<script src="/external.js"></script>'
        "<script>alert(1)</script>"
        "<script>var x = 2;</script>"
        "</body></html>",
        encoding="utf-8",
    )

    hashes = _extract_inline_script_hashes(tmp_path)

    assert len(hashes) == 2
    for h in hashes:
        assert h.startswith("'sha256-") and h.endswith("'")


def test_extract_inline_script_hashes_dedupes_across_files(tmp_path):
    """Identical inline scripts in different files collapse to a single hash."""
    (tmp_path / "a.html").write_text("<script>shared()</script>", encoding="utf-8")
    (tmp_path / "b.html").write_text("<script>shared()</script>", encoding="utf-8")

    hashes = _extract_inline_script_hashes(tmp_path)

    assert len(hashes) == 1


def test_extract_inline_script_hashes_returns_empty_when_dir_missing(tmp_path):
    """Nonexistent directory returns an empty set (not an error)."""
    assert _extract_inline_script_hashes(tmp_path / "does-not-exist") == set()


def test_extract_inline_script_hashes_matches_csp_spec(tmp_path):
    """Hash equals base64(SHA-256(script body)) — CSP3 spec."""
    body = "alert('hello')"
    (tmp_path / "page.html").write_text(
        f"<script>{body}</script>", encoding="utf-8"
    )

    hashes = _extract_inline_script_hashes(tmp_path)

    digest = hashlib.sha256(body.encode("utf-8")).digest()
    expected = f"'sha256-{base64.b64encode(digest).decode('ascii')}'"
    assert expected in hashes


def test_extract_inline_script_hashes_handles_attributes(tmp_path):
    """Inline scripts with attributes (other than src) are still hashed."""
    (tmp_path / "page.html").write_text(
        '<script id="abc" data-foo="bar">payload();</script>',
        encoding="utf-8",
    )

    hashes = _extract_inline_script_hashes(tmp_path)

    digest = hashlib.sha256(b"payload();").digest()
    expected = f"'sha256-{base64.b64encode(digest).decode('ascii')}'"
    assert expected in hashes


def test_extract_inline_script_hashes_recurses_subdirs(tmp_path):
    """Hashes found in nested directories (Next.js outputs per-route folders)."""
    (tmp_path / "login").mkdir()
    (tmp_path / "login" / "index.html").write_text(
        "<script>route()</script>", encoding="utf-8"
    )

    hashes = _extract_inline_script_hashes(tmp_path)

    assert len(hashes) == 1
