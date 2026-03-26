# SOC 2 Type II Audit — Bhapi Platform

## Overview

Bhapi is pursuing SOC 2 Type II certification for the Trust Services Criteria: Security, Availability, Confidentiality, and Privacy. This directory contains policy documents, control mappings, and evidence collection procedures.

## Timeline

- **Audit initiation:** Q3 2026
- **Observation period:** 6 months (Type II requires sustained evidence)
- **Target completion:** Q1 2027

## Documents

| Document | Purpose |
|----------|---------|
| `information-security-policy.md` | Organization-wide security policy |
| `access-control-policy.md` | Logical access, authentication, RBAC |
| `change-management-policy.md` | Code review, CI/CD, deployment controls |
| `data-classification-policy.md` | Data handling, encryption, retention |
| `control-mapping.md` | TSC criteria mapped to platform controls |

## Automated Evidence Collection

The platform auto-collects evidence via `src/compliance/soc2.py`:

- **deployment_log** — App version, deploy metadata
- **access_control** — RBAC enforcement summary
- **encryption** — Credential encryption status
- **audit_trail** — API access logs with correlation IDs

Evidence is stored in the `evidence_collections` table (migration 052) and can be exported via the compliance API.

## Database Tables (Migration 052)

- `audit_policies` — Policy versions, approval status, review dates
- `evidence_collections` — Auto-collected evidence snapshots
- `compliance_controls` — TSC control definitions with status tracking
