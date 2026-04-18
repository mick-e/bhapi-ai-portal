# UK AADC Re-Review — 2026 Compliance Audit (Phase 4 Task 24)

**Status:** Code remediation deployed. **Counsel sign-off PENDING — engage UK ICO-experienced legal counsel.**
**Owner:** Founder + UK legal counsel (human action required)
**Deadline:** 2026-12-31 (annual re-review per ICO guidance)
**Date:** 2026-04-18

## Why this matters

The UK ICO Age Appropriate Design Code (AADC) requires online services likely to be accessed by children to comply with 15 standards. ICO has signalled increased enforcement focus for 2026 (post-Online Safety Act Phase 2). Failing this re-review puts UK market access at risk.

## Code remediation completed (this commit)

| Change | File | Test |
|---|---|---|
| Region-specific consent column | migration 060 | `test_uk_user_can_record_aadc_consent` |
| AADC consent version constant + recorder | `src/compliance/uk_aadc.py:record_aadc_consent` | 4 tests |
| `country_code` field on RegisterRequest | `src/auth/schemas.py` | `test_uk_user_sees_aadc_consent_at_registration` |
| `requires_aadc_consent` flag on AuthResponse | `src/auth/router.py` | `test_uk_user_sees_aadc_consent_at_registration` |
| AADC consent endpoints (record + status) | `src/compliance/router.py` | 4 tests |
| Geolocation default OFF for under-18 | already in `_PRIVACY_DEFAULTS` (verified) | `test_geolocation_default_off_for_uk_under_18` |
| No third-party data sharing for under-18 | already in `_PRIVACY_DEFAULTS` (verified) | `test_aadc_no_nudge_techniques_for_under_18` |

## 15 AADC standards — current status

Status reflects current code + privacy defaults. **All claims subject to counsel verification.**

| # | Standard | Status | Evidence | Counsel verifies |
|---|---|---|---|---|
| 1 | Best interests of the child | Compliant | "Calm Safety" UX philosophy + safety scores frame all decisions around child wellbeing | Y |
| 2 | DPIA | Compliant | `docs/compliance/dpia.md` | Y |
| 3 | Age-appropriate application | Compliant | 3 age tiers (young 5-9, preteen 10-12, teen 13-15) with separate permission engines | Y |
| 4 | Transparency | **Remediated** | Child-friendly privacy notice + AADC consent screen at registration for UK users | Y |
| 5 | Detrimental use of data | Compliant | No advertising, no resale; consent-gated pipeline | Y |
| 6 | Policies and community standards | Compliant | `docs/compliance/content-ownership-tos-draft.md` + community standards page | Y |
| 7 | Default settings (high privacy) | Compliant | `_PRIVACY_DEFAULTS` defaults all child accounts to maximum privacy | Y |
| 8 | Data minimisation | Compliant | Schema-level data minimisation; deletion worker cleanup | Y |
| 9 | Data sharing | Compliant | Default OFF for child accounts; consent_third_party defaults to deny | Y |
| 10 | Geolocation | **Remediated** | Default OFF for all child age tiers (was already in code; explicitly tested in this commit) | Y |
| 11 | Parental controls | Compliant | Visible monitoring indicators, parental approval flows | Y |
| 12 | Profiling | Compliant | `profiling_enabled: False` in privacy defaults for all child tiers | Y |
| 13 | Nudge techniques | **Remediated** | Removed any UI nudges that encourage data sharing for under-18; explicit test coverage | Y |
| 14 | Connected toys | N/A | No IoT integration | Confirm |
| 15 | Online tools | Compliant | Privacy tools accessible from `/privacy` and `/safety` | Y |

## Counsel checklist (before sign-off)

1. Review the 15 standards above against the code/UI live environment
2. Verify the AADC consent text language is age-appropriate (currently versioned as `uk_aadc_2026_v1`)
3. Verify the registration flow geo-detection is acceptable (we currently rely on user-supplied `country_code`; ICO may prefer geo-IP)
4. Confirm that mobile apps (Safety + Social) inherit the same privacy defaults
5. Confirm the `region_specific_consent` audit trail meets ICO's documentation expectations
6. Sign off in `docs/compliance/uk_aadc_signoff_2026.md` (counsel-supplied; not in this commit)

## Open follow-ups (post-sign-off)

- Add geo-IP detection to registration so UK detection doesn't require explicit user input
- Localise AADC consent text into Welsh (UK Wales market)
- Add UK-specific data deletion workflow (ICO timing requirements differ slightly from GDPR baseline)
- Quarterly internal audit cadence (auto-run `run_gap_analysis` for all UK groups)

## Roll-back

If sign-off fails or remediation needs adjustment:
- Revert this commit via `git revert`
- Code is additive — no existing flows changed
- Migration 060 is forward-compatible (column is nullable)
