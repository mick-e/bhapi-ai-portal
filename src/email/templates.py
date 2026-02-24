"""Email templates for the Bhapi platform.

Each template function returns (subject, html_body, plain_body) tuple.
HTML uses inline styles for maximum email client compatibility.
"""

from __future__ import annotations

from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Shared layout
# ---------------------------------------------------------------------------
_HEADER = """\
<div style="background-color:#1a1a2e;padding:24px 32px;text-align:center;">
  <h1 style="color:#ffffff;font-family:Arial,sans-serif;margin:0;font-size:24px;">
    Bhapi
  </h1>
  <p style="color:#a0a0c0;font-family:Arial,sans-serif;margin:4px 0 0;font-size:13px;">
    AI Safety for Families
  </p>
</div>
"""

_FOOTER = """\
<div style="background-color:#f5f5f5;padding:16px 32px;text-align:center;font-family:Arial,sans-serif;font-size:12px;color:#888;">
  <p style="margin:0;">
    You are receiving this because you are a member of a Bhapi group.<br>
    <a href="https://bhapi.ai/settings" style="color:#6366f1;">Manage notification preferences</a>
  </p>
  <p style="margin:8px 0 0;color:#aaa;">&copy; {year} Bhapi &middot; bhapi.ai</p>
</div>
"""


def _wrap(body_html: str) -> str:
    """Wrap body content in the standard email layout."""
    year = datetime.now(timezone.utc).year
    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body style="margin:0;padding:0;background:#f0f0f5;">'
        '<div style="max-width:600px;margin:0 auto;background:#ffffff;border-radius:8px;overflow:hidden;'
        'box-shadow:0 2px 8px rgba(0,0,0,0.08);">'
        f"{_HEADER}"
        f'<div style="padding:24px 32px;font-family:Arial,sans-serif;color:#333;line-height:1.6;">'
        f"{body_html}"
        "</div>"
        f"{_FOOTER.format(year=year)}"
        "</div></body></html>"
    )


# ---------------------------------------------------------------------------
# Severity styling
# ---------------------------------------------------------------------------
_SEVERITY_COLORS = {
    "critical": ("#dc2626", "#fef2f2"),  # red
    "high": ("#ea580c", "#fff7ed"),       # orange
    "medium": ("#ca8a04", "#fefce8"),     # yellow
    "low": ("#2563eb", "#eff6ff"),        # blue
    "info": ("#6b7280", "#f9fafb"),       # gray
}


# ---------------------------------------------------------------------------
# 1. Risk alert email
# ---------------------------------------------------------------------------
def risk_alert(
    *,
    member_name: str,
    severity: str,
    category: str,
    category_description: str,
    platform: str,
    confidence: float,
    reasoning: str,
    group_name: str,
    alert_url: str,
) -> tuple[str, str, str]:
    """Immediate risk alert email sent to group admins."""
    fg, bg = _SEVERITY_COLORS.get(severity, _SEVERITY_COLORS["info"])

    subject = f"[{severity.upper()}] {category_description} — {member_name}"

    body = f"""\
<div style="background:{bg};border-left:4px solid {fg};padding:12px 16px;border-radius:4px;margin-bottom:16px;">
  <strong style="color:{fg};font-size:16px;">{severity.upper()} Risk Detected</strong>
</div>

<table style="width:100%;border-collapse:collapse;margin-bottom:16px;">
  <tr><td style="padding:6px 0;color:#666;width:120px;">Member</td><td style="padding:6px 0;font-weight:bold;">{member_name}</td></tr>
  <tr><td style="padding:6px 0;color:#666;">Category</td><td style="padding:6px 0;">{category_description}</td></tr>
  <tr><td style="padding:6px 0;color:#666;">Platform</td><td style="padding:6px 0;">{platform}</td></tr>
  <tr><td style="padding:6px 0;color:#666;">Confidence</td><td style="padding:6px 0;">{confidence:.0%}</td></tr>
  <tr><td style="padding:6px 0;color:#666;">Group</td><td style="padding:6px 0;">{group_name}</td></tr>
</table>

<p><strong>Details:</strong> {reasoning}</p>

<div style="text-align:center;margin:24px 0;">
  <a href="{alert_url}" style="display:inline-block;background:#6366f1;color:#fff;padding:12px 32px;
     text-decoration:none;border-radius:6px;font-weight:bold;">View Alert</a>
</div>
"""

    plain = (
        f"{severity.upper()} Risk Detected\n\n"
        f"Member: {member_name}\n"
        f"Category: {category_description}\n"
        f"Platform: {platform}\n"
        f"Confidence: {confidence:.0%}\n"
        f"Group: {group_name}\n\n"
        f"Details: {reasoning}\n\n"
        f"View alert: {alert_url}\n"
    )

    return subject, _wrap(body), plain


# ---------------------------------------------------------------------------
# 2. Alert digest email
# ---------------------------------------------------------------------------
def alert_digest(
    *,
    group_name: str,
    period: str,
    total_alerts: int,
    by_severity: dict[str, int],
    alert_summaries: list[dict],
    dashboard_url: str,
) -> tuple[str, str, str]:
    """Batched alert digest email (hourly or daily)."""
    subject = f"Bhapi {period} digest — {total_alerts} alert{'s' if total_alerts != 1 else ''}"

    severity_rows = ""
    for sev in ("critical", "high", "medium", "low"):
        count = by_severity.get(sev, 0)
        if count > 0:
            fg, _ = _SEVERITY_COLORS.get(sev, _SEVERITY_COLORS["info"])
            severity_rows += (
                f'<span style="display:inline-block;background:{fg};color:#fff;'
                f'padding:2px 10px;border-radius:12px;font-size:12px;margin-right:8px;">'
                f"{sev}: {count}</span>"
            )

    alert_list = ""
    for a in alert_summaries[:20]:
        fg, bg = _SEVERITY_COLORS.get(a.get("severity", "info"), _SEVERITY_COLORS["info"])
        alert_list += (
            f'<div style="border-bottom:1px solid #eee;padding:8px 0;">'
            f'<span style="color:{fg};font-weight:bold;">[{a.get("severity", "").upper()}]</span> '
            f'{a.get("title", "")}'
            f'<span style="color:#999;font-size:12px;margin-left:8px;">{a.get("member_name", "")}</span>'
            f"</div>"
        )

    body = f"""\
<h2 style="margin-top:0;">Your {period} summary for {group_name}</h2>

<p><strong>{total_alerts}</strong> alert{'s' if total_alerts != 1 else ''} in this period:</p>
<div style="margin-bottom:16px;">{severity_rows}</div>

<div style="margin-bottom:16px;">{alert_list}</div>

<div style="text-align:center;margin:24px 0;">
  <a href="{dashboard_url}" style="display:inline-block;background:#6366f1;color:#fff;padding:12px 32px;
     text-decoration:none;border-radius:6px;font-weight:bold;">View Dashboard</a>
</div>
"""

    plain_alerts = "\n".join(
        f"- [{a.get('severity', '').upper()}] {a.get('title', '')} ({a.get('member_name', '')})"
        for a in alert_summaries[:20]
    )
    plain = (
        f"Your {period} summary for {group_name}\n\n"
        f"{total_alerts} alerts in this period.\n\n"
        f"{plain_alerts}\n\n"
        f"View dashboard: {dashboard_url}\n"
    )

    return subject, _wrap(body), plain


# ---------------------------------------------------------------------------
# 3. Email verification
# ---------------------------------------------------------------------------
def email_verification(
    *,
    display_name: str,
    verification_url: str,
) -> tuple[str, str, str]:
    """Email verification sent after registration."""
    subject = "Verify your Bhapi email address"

    body = f"""\
<h2 style="margin-top:0;">Welcome to Bhapi, {display_name}!</h2>

<p>Please verify your email address to complete your registration and start
protecting your family's AI interactions.</p>

<div style="text-align:center;margin:24px 0;">
  <a href="{verification_url}" style="display:inline-block;background:#6366f1;color:#fff;padding:12px 32px;
     text-decoration:none;border-radius:6px;font-weight:bold;">Verify Email</a>
</div>

<p style="color:#888;font-size:13px;">
  This link expires in 24 hours. If you didn't create a Bhapi account, you can
  safely ignore this email.
</p>
"""

    plain = (
        f"Welcome to Bhapi, {display_name}!\n\n"
        f"Please verify your email address:\n{verification_url}\n\n"
        "This link expires in 24 hours.\n"
    )

    return subject, _wrap(body), plain


# ---------------------------------------------------------------------------
# 4. Password reset
# ---------------------------------------------------------------------------
def password_reset(
    *,
    display_name: str,
    reset_url: str,
) -> tuple[str, str, str]:
    """Password reset email."""
    subject = "Reset your Bhapi password"

    body = f"""\
<h2 style="margin-top:0;">Password Reset</h2>

<p>Hi {display_name}, we received a request to reset your Bhapi password.</p>

<div style="text-align:center;margin:24px 0;">
  <a href="{reset_url}" style="display:inline-block;background:#6366f1;color:#fff;padding:12px 32px;
     text-decoration:none;border-radius:6px;font-weight:bold;">Reset Password</a>
</div>

<p style="color:#888;font-size:13px;">
  This link expires in 1 hour. If you didn't request a password reset,
  you can safely ignore this email. Your password will not be changed.
</p>
"""

    plain = (
        f"Hi {display_name},\n\n"
        f"Reset your password: {reset_url}\n\n"
        "This link expires in 1 hour.\n"
    )

    return subject, _wrap(body), plain


# ---------------------------------------------------------------------------
# 5. Group invitation
# ---------------------------------------------------------------------------
def group_invitation(
    *,
    inviter_name: str,
    group_name: str,
    role: str,
    invitation_url: str,
) -> tuple[str, str, str]:
    """Group invitation email."""
    subject = f"You've been invited to join {group_name} on Bhapi"

    body = f"""\
<h2 style="margin-top:0;">You're Invited!</h2>

<p><strong>{inviter_name}</strong> has invited you to join
<strong>{group_name}</strong> as a <strong>{role}</strong>.</p>

<p>Bhapi helps families monitor and manage their children's AI interactions,
providing real-time safety alerts and usage insights.</p>

<div style="text-align:center;margin:24px 0;">
  <a href="{invitation_url}" style="display:inline-block;background:#6366f1;color:#fff;padding:12px 32px;
     text-decoration:none;border-radius:6px;font-weight:bold;">Accept Invitation</a>
</div>

<p style="color:#888;font-size:13px;">
  This invitation expires in 7 days.
</p>
"""

    plain = (
        f"{inviter_name} has invited you to join {group_name} as a {role}.\n\n"
        f"Accept: {invitation_url}\n\n"
        "This invitation expires in 7 days.\n"
    )

    return subject, _wrap(body), plain


# ---------------------------------------------------------------------------
# 6. Report ready
# ---------------------------------------------------------------------------
def report_ready(
    *,
    report_type: str,
    group_name: str,
    period: str,
    download_url: str,
) -> tuple[str, str, str]:
    """Notification that a scheduled report is ready."""
    subject = f"Your {report_type} report for {group_name} is ready"

    body = f"""\
<h2 style="margin-top:0;">Report Ready</h2>

<p>Your <strong>{report_type}</strong> report for <strong>{group_name}</strong>
covering <strong>{period}</strong> is ready to download.</p>

<div style="text-align:center;margin:24px 0;">
  <a href="{download_url}" style="display:inline-block;background:#6366f1;color:#fff;padding:12px 32px;
     text-decoration:none;border-radius:6px;font-weight:bold;">Download Report</a>
</div>

<p style="color:#888;font-size:13px;">
  This download link expires in 7 days.
</p>
"""

    plain = (
        f"Your {report_type} report for {group_name} ({period}) is ready.\n\n"
        f"Download: {download_url}\n\n"
        "Link expires in 7 days.\n"
    )

    return subject, _wrap(body), plain
