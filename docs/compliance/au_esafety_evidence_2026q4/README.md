# Australia eSafety Evidence Package — 2026 Q4 Production Sign-Off

**Status:** Evidence assembled. **Counsel sign-off PENDING — engage AU-registered compliance counsel.**
**Owner:** Founder + Australian legal counsel (human action required)
**Date:** 2026-04-19

## Purpose

This package consolidates code references, test evidence, and operational records proving Bhapi's compliance with the Australian Online Safety Act 2021 (OSA) and the Social Media Minimum Age Act 2024. The goal is to give Australian counsel everything they need to issue a sign-off letter for AU market production launch.

## How to use

1. Counsel reviews each evidence file against the corresponding eSafety requirement in `docs/compliance/australian-online-safety-analysis.md`
2. Counsel runs the tests referenced to confirm code matches claims
3. Counsel writes a sign-off letter at `docs/compliance/au_esafety_signoff_2026q4.md` (not in this commit — counsel-supplied)
4. On sign-off, `project_bhapi_unified_roadmap.md` is updated to mark AU market "CLEARED"

## Evidence files

| Area | File | eSafety requirement |
|---|---|---|
| Age verification | `01-age-verification.md` | Social Media Minimum Age Act 2024 (U16 ban) |
| Content takedown SLA | `02-content-takedown-sla.md` | OSA Part 3 (cyberbullying) + Part 6 (IBA) 24h SLA |
| BOSE expectations | `03-bose-compliance.md` | OSA Part 4 Basic Online Safety Expectations |
| CSAM detection | `04-csam-detection.md` | OSA Part 9 + Phase 2 industry codes |
| Image-based abuse | `05-image-based-abuse.md` | OSA Part 6 IBA scheme |
| VPN/bypass detection | `06-vpn-bypass-detection.md` | "Reasonable steps" under s63F |
| Moderation queue | `07-moderation-queue.md` | Phase 2 industry codes |
| Reporting & complaints | `08-reporting-complaints.md` | OSA Part 3 complaints handling |
| AU contact point | `09-au-contact-point.md` | BOSE designated contact |

## Open questions for counsel

1. Section 63C classification — does Bhapi Social qualify for the parental-control-software exemption? See `docs/compliance/australian-online-safety-analysis.md §3`.
2. VPN/proxy detection we ship (R-24) — is this sufficient as "reasonable steps"? Or does the Act require active blocking of evasion?
3. Does our U16 hard gate (Safety features only for under-16 AU users) meet the minimum-age requirement, or do we need to also block AU under-16 users from creating Bhapi accounts entirely?
4. eSafety reporting — is the internal incident-management system (no public API exists) acceptable as a "good faith" reporting mechanism?

## Sign-off checklist (for counsel)

- [ ] All 9 evidence files reviewed against code and tests
- [ ] Age verification flow accepted as meeting Social Media Minimum Age Act (or exemption confirmed)
- [ ] BOSE contact point designated in writing (email + phone + response SLA)
- [ ] 24h takedown SLA monitoring reviewed and approved
- [ ] CSAM detection (PhotoDNA) + NCMEC reporting pathway reviewed
- [ ] VPN/bypass detection accepted as reasonable steps
- [ ] Sign-off letter drafted at `docs/compliance/au_esafety_signoff_2026q4.md`
- [ ] Professional liability insurance confirmed for AU market
