# COPPA 2026 Consent Enforcement — Design Spec

**Date:** 2026-03-18
**Deadline:** 2026-04-22 (35 days)
**Status:** Approved
**Approach:** Option A — Centralized Consent Gate

## Problem

The platform collects and manages per-provider third-party consent (7 providers) and push notification consent (3 types), but never enforces them. Third-party APIs are called regardless of consent state. This is a COPPA 2026 regulatory violation.

## Scope

5 enforcement gaps + 2 UX gaps:

1. **Third-party consent enforcement** — gate SendGrid, Twilio, Google Cloud AI, Hive/Sensity, Yoti calls on consent
2. **Push notification consent enforcement** — gate alert delivery on notification type consent
3. **Risk pipeline context threading** — pass group_id/member_id/db through pipeline so layers can check consent
4. **Degraded mode** — graceful fallback when consent missing (keyword-only classifier, skip deepfake, skip email/SMS)
5. **Yoti consent check** — gate verification initiation on consent
6. **Privacy notice at registration** — require acceptance before account creation
7. **Age-gating** — block monitoring features for children <13 without signed family agreement

## Out of Scope

- Child-friendly privacy notice (i18n) — separate task
- Parental data collection dashboard — separate task
- Yoti webhook for auto-completion — separate task
- Safe harbor certificate generation — separate task

## Design

### 1. Consent Check Helpers

**File:** `src/compliance/coppa_2026.py`

```python
async def check_third_party_consent(
    db: AsyncSession, group_id: UUID, member_id: UUID, provider_key: str
) -> bool:
    """Check if parent consented to share child data with a third-party provider.
    Returns True only if an explicit consent record exists with consented=True
    and withdrawn_at is None. Returns False if no record exists or if withdrawn.
    Uses get_third_party_consents() internally which auto-creates default records
    (consented=False) if none exist."""

async def check_push_notification_consent(
    db: AsyncSession, group_id: UUID, member_id: UUID, notification_type: str
) -> bool:
    """Check if parent consented to receive a specific notification type.
    Returns True only if explicit consent record exists with consented=True.
    Returns False if no record or if explicitly withdrawn."""
```

Default behavior: consent defaults to `False` (deny-by-default). The existing `_create_default_consent_items()` creates records with `consented=False`. This is correct for COPPA — no data sharing until parent explicitly opts in.

### 2. Risk Pipeline Context Threading

**File:** `src/risk/engine.py`

Modify `process_event()` signature:
```python
async def process_event(
    capture_event_data: dict,
    member_age: int | None = None,
    config: dict[str, dict] | None = None,
    # NEW parameters:
    group_id: UUID | None = None,
    member_id: UUID | None = None,
    db: AsyncSession | None = None,
) -> list[RiskClassification]:
```

Pass to layers that call external APIs:
- `_layer_deepfake_detection(media_urls, group_id, member_id, db)` — checks `hive_sensity` consent
- `_layer_safety_classification(content, group_id, member_id, db)` — checks `google_cloud_ai` consent

When consent missing:
- **Google Cloud AI** → pass `force_keyword_only=True` to `classify_safety()` which overrides the global `safety_classifier_mode` setting for this call only
- **Hive/Sensity** → skip detection, return empty list
- Log degradation via structlog with `consent_degraded=True, provider=<key>`

Layers that don't call external APIs (`_layer_pii_detection`, `_layer_rules_engine`) are unchanged.

**Caller update:** `src/risk/pipeline.py` already has `group_id`, `member_id`, and `db` available — pass them through.

### 3. Alert Delivery Enforcement

**File:** `src/alerts/delivery.py`

In `deliver_alert_email()`:
1. Skip consent checks if `alert.member_id is None` (system/group-level alerts always deliver)
2. Check `check_third_party_consent(db, alert.group_id, alert.member_id, "sendgrid")`
3. Check `check_push_notification_consent(db, alert.group_id, alert.member_id, notification_type)`
   - Map alert severity to notification type: critical/high → `risk_alerts`, summary → `activity_summaries`, weekly → `weekly_reports`
4. If either check fails, skip delivery and log

**File:** `src/sms/service.py`

In `send_sms()`:
1. Add `member_id: UUID | None = None` and `db: AsyncSession | None = None` parameters
2. If `group_id`, `member_id`, and `db` are all provided, check `check_third_party_consent(db, group_id, member_id, "twilio_sms")`
3. If not consented, skip and log
4. Update all callers of `send_sms()` to pass `db` and `member_id` where available

### 4. Yoti Consent Check

**File:** `src/compliance/coppa_2026.py`

In `initiate_video_verification()`:
1. Look up the parent's `GroupMember.id` from their `user_id` (the consent table is keyed on member_id, not user_id)
2. Before `create_age_verification_session()` call, check `check_third_party_consent(db, group_id, parent_member_id, "yoti")`
3. If not consented, raise `ForbiddenError("Yoti verification requires consent to Yoti data sharing")`
4. If parent has no GroupMember record (edge case), skip consent check and allow (parent is not a child)

### 5. Degraded Mode Response

Keep `process_event()` return type as `list[RiskClassification]` (no breaking change). Communicate degradation through structlog context — each skipped provider logs `consent_degraded=True, provider=<key>, group_id=<id>`.

Add a separate utility for frontend queries:
```python
async def get_degraded_providers(db, group_id, member_id) -> list[str]:
    """Return list of provider keys where consent is not granted."""
```

The dashboard can call this to show: "Some safety features are limited. Enable Google Cloud AI in Privacy Settings for full protection."

### 6. Privacy Notice at Registration

**File:** `src/auth/router.py`

Add `privacy_notice_accepted: bool` field to registration schema. Validate it's `True` before creating account. Log acceptance in audit trail via `audit_logger.log()` (no new migration needed — uses existing `AuditLog` table with action `privacy_notice_accepted`).

**File:** `portal/src/app/(auth)/register/page.tsx`

Add privacy consent checklist before submit:
- "I understand my child's AI interactions will be collected and analyzed"
- "I understand data may be shared with third-party providers (configurable in Privacy Settings)"
- "I have read the Privacy Policy"
- Checkbox must be checked to enable Register button

### 7. Age-Gating

**File:** `src/groups/service.py`

Add `check_family_agreement_signed(db, group_id, member_id) -> bool`:
- Query `FamilyAgreement` for the group
- Check if member has signed it
- Return False if no agreement exists or member hasn't signed
- Export via `src/groups/__init__.py` public interface

**File:** `src/capture/service.py`

In `ingest_event()`, after existing consent check:
- Import from `src.groups` (package), not `src.groups.service` (follows existing pattern from `check_member_consent`)
- If member age < 13 and `check_family_agreement_signed()` returns False, raise `ForbiddenError`

### 8. Tests

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `tests/unit/test_consent_enforcement.py` | 12 | check_third_party_consent, check_push_notification_consent, defaults, withdrawal |
| `tests/e2e/test_consent_enforcement_e2e.py` | 15 | Pipeline degraded mode, alert skipping, SMS skipping, Yoti blocking |
| `tests/security/test_consent_bypass_security.py` | 8 | Verify no bypass paths for all 5 providers |
| `tests/unit/test_privacy_notice.py` | 4 | Registration with/without notice acceptance |
| `tests/unit/test_age_gating.py` | 6 | Agreement check, capture blocking for minors |

## File Changes Summary

| File | Change Type | Description |
|------|------------|-------------|
| `src/compliance/coppa_2026.py` | Modify | Add check_third_party_consent, check_push_notification_consent, get_degraded_providers, Yoti consent gate |
| `src/risk/engine.py` | Modify | Thread context params, add consent checks in deepfake + safety layers |
| `src/risk/pipeline.py` | Modify | Pass group_id/member_id/db to process_event |
| `src/risk/safety_classifier.py` | Modify | Add force_keyword_only param to classify_safety() |
| `src/alerts/delivery.py` | Modify | Add SendGrid + push consent checks (skip when member_id is None) |
| `src/sms/service.py` | Modify | Add db + member_id params, Twilio consent check |
| `src/auth/router.py` | Modify | Privacy notice acceptance on registration |
| `src/auth/schemas.py` | Modify | Add privacy_notice_accepted field |
| `src/groups/service.py` | Modify | Add check_family_agreement_signed |
| `src/groups/__init__.py` | Modify | Export check_family_agreement_signed |
| `src/capture/service.py` | Modify | Add age-gating check |
| `portal/src/app/(auth)/register/page.tsx` | Modify | Privacy consent checklist UI |
| 5 new test files | Create | Unit, E2E, security tests |

## Migration

No new migration needed — all models (`ThirdPartyConsentItem`, `PushNotificationConsent`, `FamilyAgreement`) already exist in migrations 017 and 031.
