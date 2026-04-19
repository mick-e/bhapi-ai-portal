# 03 — Basic Online Safety Expectations (BOSE, OSA Part 4)

**Requirement:** Take reasonable steps to ensure user safety; provide complaint mechanisms; proactively minimise harmful material; respond to eSafety notices; designate a contact point.

## BOSE-by-BOSE

| BOSE expectation | Bhapi implementation | Evidence file |
|---|---|---|
| Safety by design | "Calm Safety" UX philosophy; maximum-privacy defaults for children | `src/compliance/uk_aadc.py:_PRIVACY_DEFAULTS` |
| Proactive minimisation of harm | Pre-publish moderation for under-13, post-publish <60s takedown for 13-15 | `02-content-takedown-sla.md` |
| Complaint mechanism | In-product "Report" on all social content + email to `safety@bhapi.ai` | `src/moderation/reporting.py` |
| Response to eSafety notices | Dedicated intake workflow; 24h SLA; audit trail | `02-content-takedown-sla.md` + `08-reporting-complaints.md` |
| Transparency | Public transparency report (planned Q4 2026) with volume of reports, actions taken, SLA compliance | Roadmap |
| Designated contact point | `safety@bhapi.ai` + named compliance officer | `09-au-contact-point.md` |
| CSAM minimisation | PhotoDNA + NCMEC reporting | `04-csam-detection.md` |
| Deepfake IBA minimisation | Deepfake detection (Hive/Sensity) + IBA removal workflow | `05-image-based-abuse.md` |

## Code references

- `src/risk/` — 14-category risk taxonomy including bullying, sexual content, self-harm
- `src/moderation/` — moderation pipeline with keyword + image + video + social risk classifiers
- `src/alerts/` — calm parent-friendly alert templates
- `src/compliance/coppa_2026.py` — safety-by-default enforcement

## Tests

- `tests/e2e/test_moderation.py` — end-to-end moderation pipeline
- `tests/e2e/test_csam_detection.py` — CSAM classifier coverage
- `tests/e2e/test_deepfake_detection.py` — deepfake/IBA detection
- `tests/security/test_moderation_security.py` — moderator access control

## Counsel review items

- BOSE compliance is not directly enforceable, but Bhapi's stance is that we comply proactively. Is the evidence sufficient to establish that claim?
- Do we need a public transparency report published before AU launch, or is "planned Q4 2026" acceptable as a written commitment?
