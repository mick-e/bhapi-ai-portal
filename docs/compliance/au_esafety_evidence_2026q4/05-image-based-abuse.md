# 05 — Image-Based Abuse (IBA, OSA Part 6)

**Requirement:** Respond to IBA removal notices within 24 hours. Handle AI-generated deepfake intimate images.

## Code references

- `src/risk/deepfake.py` — deepfake detection via Hive or Sensity
- `src/moderation/iba_handler.py` — IBA-specific takedown workflow
- `src/risk/service.py` — classification of intimate content with consent signal

## Flow

1. User uploads image → deepfake classifier runs in parallel with moderation pipeline
2. Suspected deepfake intimate image → blocked from publish, flagged for review
3. User reports IBA content → handled via `POST /api/v1/moderation/iba-report`
4. eSafety removal notice → handled via dedicated intake at `safety@bhapi.ai` with 24h SLA

## Tests

- `tests/e2e/test_deepfake_detection.py` — classifier coverage
- `tests/e2e/test_iba_workflow.py` — end-to-end IBA report to removal
- `tests/unit/test_deepfake_providers.py` — Hive + Sensity adapter tests

## Operational

- Hive API: `DEEPFAKE_PROVIDER=hive` + `DEEPFAKE_API_KEY`
- Sensity API: `DEEPFAKE_PROVIDER=sensity` + `DEEPFAKE_API_KEY`
- Response SLA to user-submitted IBA reports: <60s (pre-publish moderation) or <24h (takedown notice)

## Counsel review items

- Are Hive and Sensity acceptable deepfake-detection providers per eSafety's Phase 2 industry code expectations?
- Do we need to proactively scan historical content for IBA, or is inbound moderation + user reports sufficient?
- What's the legal treatment of AI-generated intimate images where the subject is identifiable but not a real person? (AI-generated deepfakes of real minors are CSAM per most jurisdictions)
