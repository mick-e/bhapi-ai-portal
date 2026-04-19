# 01 — Age Verification (Social Media Minimum Age Act 2024)

**Requirement:** Under-16 Australian users must be blocked from social media services. Age verification must be "reasonable" — Yoti or equivalent is acceptable to eSafety per the Phase 2 industry codes.

## Code references

- `src/integrations/yoti_client.py` — Yoti age verification integration
- `src/age_tier/` — 3-tier permission engine (young 5-9, preteen 10-12, teen 13-15)
- `src/age_tier/service.py:assign_tier()` — tier assignment from DOB
- `src/auth/router.py:/register` — registration with `country_code` + DOB validation
- `src/groups/router.py` — AU-specific jurisdiction checks

## Flow (AU users)

1. User registers. `country_code=AU` triggers AU path.
2. Yoti age verification is required before any social endpoint is accessible.
3. If age < 16: social features hard-gated (403 Forbidden on all `/api/v1/social/*`); Safety features available.
4. If age ≥ 16: full platform access per existing age-tier rules.

## Tests

- `tests/e2e/test_age_verification.py` — Yoti flow coverage
- `tests/e2e/test_age_tier.py` — tier assignment and enforcement
- `tests/e2e/test_australian_compliance.py` — AU-specific gate
- `tests/e2e/test_australian_safety.py` — under-16 AU hard gate

## Operational

- Yoti credentials stored via `YOTI_CLIENT_SDK_ID` + `YOTI_PEM_FILE_PATH` (encrypted via `src/encryption.py`)
- Verification records persisted in `VideoVerification` model (see `src/compliance/models.py`)
- Audit trail in `audit_entries` table with `action=age_verification_completed`

## Counsel review items

- Is Yoti sufficient as "reasonable steps"? (Phase 2 industry codes appear to accept it)
- Do we need parental attestation as a fallback when Yoti fails?
- Is the under-16 hard gate at the API level acceptable, or is UI-level gating also required?
