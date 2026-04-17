# SOC 2 Type II — Gap Assessment

> **Status:** PENDING (awaiting auditor engagement — Task 9)
> **Owner:** Head of Engineering + Compliance Analyst

## Purpose

Identify gaps between current Bhapi controls and SOC 2 Trust Service Criteria requirements. This assessment feeds directly into the control inventory (scripts/soc2/control_inventory.yaml) and the evidence collector (scripts/soc2/evidence_collector.py).

## Current Control Posture (Pre-Assessment)

Based on existing implementation:

### Likely Strong Areas
- **Access control**: JWT + API key auth, RBAC with scoped permissions, session management
- **Encryption**: Fernet/KMS credential encryption, TLS in transit, HSTS preload
- **Logging**: Structured JSON logging with correlation IDs, request logging middleware
- **Change management**: GitHub Actions CI, automated tests (4600+ backend, 1035 security)
- **Incident response**: `docs/security/incident-response-plan.md` exists
- **Data retention**: Soft delete with TTL cleanup, GDPR/COPPA deletion workers

### Likely Gap Areas
- **Formal risk assessment**: No documented annual risk assessment process
- **Vendor management**: No formal vendor security review process
- **Business continuity**: No documented BCP/DR plan
- **Security awareness training**: No training program documented
- **Penetration testing**: No formal pen test report on file
- **Background checks**: No documentation of employee screening

## Assessment Process

Once auditor is engaged (Task 9):

1. Auditor provides readiness checklist
2. Map each TSC control to existing evidence or identify gap
3. Populate `scripts/soc2/control_inventory.yaml` with control-to-evidence mapping
4. Build `scripts/soc2/evidence_collector.py` to auto-export evidence from GitHub/Render
5. Prioritize gaps by auditor guidance
6. Create remediation plan with timeline

## Control Inventory Location

See `scripts/soc2/control_inventory.yaml` (to be populated after auditor kickoff).
