# AGENTS.md — Bhapi AI Portal

## Paperclip Integration

- **Company**: MickE Ventures
- **Project**: Bhapi AI Portal
- **Company ID**: `914d3bfd-0b16-4395-9d3c-61cf1d38548b`
- **Project ID**: `24048f3b-ce3a-4f9d-b4f1-9cf3deb426d2`
- **Paperclip API**: `http://localhost:3100`
- **Domain**: bhapi.com (US registered)
- **Brand**: Orange `#FF6B35` primary, Teal `#0D9488` accent

## Assigned Agents

| Agent | Title | ID | Responsibility |
|-------|-------|----|----------------|
| Portal Dev | Senior Engineer - Bhapi | `99c8f64e-1ac5-43df-9741-18f76f2c384f` | Primary development |
| Gatekeeper | Head of QA | `576379be-4e55-4d62-aea7-3719eb4a459b` | Quality strategy |
| Test Runner | QA Engineer - Backend | `66c2c3d7-7201-4529-b28a-478daf7ff2d6` | pytest (2699+ tests) |
| UI Tester | QA Engineer - Frontend | `c13df3f6-ec4d-4996-8e63-15fa118b2111` | vitest, Playwright, mobile |
| Deployer | Head of DevOps | `266f82e0-a653-4fb0-8220-209e6238bd0c` | CI/CD, Render |
| Pipeline | DevOps Engineer | `aa1789a5-c9f1-4efe-981f-29c3ad27efc6` | GitHub Actions, Docker |
| Sentinel | Head of Cybersecurity | `e1b9672a-b0ec-4864-b32c-ef65f06d1107` | Security posture |
| Scanner | Security Analyst | `4fc7896c-bdfe-442e-a33b-b942ebbab0e2` | Vulnerability scanning |
| Responder | Head of Support | `c893de84-9628-4927-8527-17559e62f408` | Incident response |
| Triager | Support Engineer | `23761b5e-604a-4072-b946-4d8e24818625` | Bug triage |
| Auditor | Compliance Analyst | `20400aed-8295-4b2f-aae5-9e7e21aa8495` | COPPA 2026 (deadline 2026-04-22) |

## Project Context

- **Stack**: FastAPI + Next.js + Expo mobile + Browser extension
- **Version**: v4.0.0 (Launch Excellence complete)
- **Backend**: 26 modules, ~250+ routes, `src/main.py`
- **Frontend**: `portal/` (Next.js App Router)
- **Mobile**: `mobile/` (Expo SDK 52+, Safety + Social apps)
- **Extension**: `extension/` (Manifest V3, Chrome + Firefox + Safari)
- **Real-time**: `src/realtime/` (WebSocket, Redis pub/sub)
- **DB**: SQLAlchemy async + Alembic (53 migrations), PostgreSQL
- **Tests**: 4639+ backend, 1035 security, 1766 E2E, 174+ frontend, 665+ mobile, 43 extension
- **Deploy**: Render (auto from master), GitHub Actions CI

## Critical Deadlines

- **COPPA 2026 enforcement**: 2026-04-22 (deny-by-default consent, child-friendly privacy notices, parental data dashboard, safe harbor certificates)

## Codebase Gotchas

- Test fixture is `test_session`, not `session`
- Registration requires `privacy_notice_accepted: True`
- Capture for children <13 requires signed FamilyAgreement
- User model uses `password_hash` (not `hashed_password`) and `email_verified` (not `is_verified`)
- Family member cap is 5
- `.test` email TLD is rejected
- BudgetThreshold uses `type` not `threshold_type`
