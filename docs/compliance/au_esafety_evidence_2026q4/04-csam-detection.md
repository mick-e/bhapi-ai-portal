# 04 — CSAM Detection (OSA Part 9 + Phase 2 industry codes)

**Requirement:** Mandatory detection and reporting of Child Sexual Abuse Material. Phase 2 industry codes (effective 2026-03-09) require hash-matching against known CSAM and reporting to authorities.

## Code references

- `src/moderation/csam_classifier.py` — PhotoDNA hash matching
- `src/moderation/ncmec_reporter.py` — NCMEC CyberTipline integration
- `src/moderation/service.py` — CSAM branch runs before any other moderation (zero-tolerance)

## Flow

1. Any user-uploaded image/video passes through PhotoDNA hash check first
2. On match: content is quarantined, user account is frozen pending review, NCMEC report is auto-generated
3. Human reviewer confirms and files the NCMEC CyberTipline report
4. Audit entry with `action=csam_detected` logged for compliance trail

## Tests

- `tests/e2e/test_csam_detection.py` — hash-match pathway
- `tests/e2e/test_ncmec_reporting.py` — NCMEC report generation (mocked)
- `tests/security/test_csam_handling.py` — quarantine + access control

## Operational

- PhotoDNA API key: `PHOTODNA_API_KEY` (encrypted)
- NCMEC CyberTipline credentials: `NCMEC_CLIENT_ID` + `NCMEC_CLIENT_SECRET`
- Response SLA: CSAM detection must complete within 2s (enforced by moderation pre-publish pipeline)

## Counsel review items

- Does our PhotoDNA integration count as sufficient hash matching? (Microsoft-maintained DB accepted by eSafety per Phase 2 codes)
- NCMEC is US-based — does eSafety accept NCMEC reporting or do we need a parallel AU-specific reporting pathway?
- Is our human-review gate before NCMEC submission acceptable, or does eSafety expect automated submission?
