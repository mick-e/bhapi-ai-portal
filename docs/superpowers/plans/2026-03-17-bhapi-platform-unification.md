# Bhapi Platform Unification — Master Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify all Bhapi products (AI Portal, Social App, Back-Office) into a single "Bhapi Platform" codebase, achieve regulatory compliance (COPPA 2026, EU AI Act, Ohio AI mandate), eliminate critical tech debt and security vulnerabilities, and ship competitive features to defend market position against GoGuardian, Bark, and Aura.

**Architecture:** The AI Portal repository (`bhapi-ai-portal`) becomes the sole active codebase per ADR-005. Legacy `bhapi-inc` repos are archived. Social features are built as new FastAPI modules per ADR-002. MongoDB data migrates to PostgreSQL per ADR-003. Mobile app is greenfielded on Expo SDK 52+ per ADR-004. Auth unifies under the Portal's JWT + API key system per ADR-001.

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy async / Alembic / PostgreSQL 16 | Next.js 15 / React 19 / TypeScript / Tailwind | Expo SDK 52+ / React Native 0.76+ / TypeScript | Manifest V3 browser extension | Redis (optional) | Stripe | Render

**Program Duration:** 6 months (March 17 — September 17, 2026)
**Regulatory Deadlines:** COPPA 2026 (Apr 22), Ohio AI Mandate (Jul 1), EU AI Act (Aug 2)

---

## Program Structure

This master plan is organized as **7 sub-plans** executed across 4 phases. Each sub-plan produces working, testable software independently but has explicit dependencies on other sub-plans where they exist.

```
PHASE 0: Emergency Stabilization (Weeks 1-5, Mar 17 — Apr 22)
  ├── Sub-Plan 1: COPPA 2026 Compliance         [REGULATORY DEADLINE: Apr 22]
  ├── Sub-Plan 2: Legacy Security & Archival     [CRITICAL TECH DEBT]
  └── Sub-Plan 3: Platform Unification Foundation [ARCHITECTURAL]

PHASE 1: Moat Defense (Weeks 6-12, Apr 23 — Jun 8)
  ├── Sub-Plan 4: School Market Entry            [COMPETITIVE]
  └── Sub-Plan 5: Social Module Foundation       [PRODUCT EXPANSION]

PHASE 2: Platform Expansion (Weeks 13-20, Jun 9 — Aug 3)
  ├── Sub-Plan 6: Mobile App & Device Agent      [COMPETITIVE]
  └── Sub-Plan 4 (cont): EU AI Act Compliance    [REGULATORY DEADLINE: Aug 2]

PHASE 3: Competitive Parity (Weeks 21-26, Aug 4 — Sep 17)
  └── Sub-Plan 7: Competitive Features & Bundle  [MARKET EXPANSION]
```

### Dependency Map

```
Sub-Plan 1 (COPPA) ──────────────────────────────────────────────► All plans inherit compliance
Sub-Plan 2 (Legacy) ─► Sub-Plan 3 (Unification) ─► Sub-Plan 5 (Social)
                                                  ─► Sub-Plan 6 (Mobile)
Sub-Plan 3 (Unification) ─► Sub-Plan 4 (School) ─► Sub-Plan 7 (Bundle)
Sub-Plan 5 (Social) ──────► Sub-Plan 6 (Mobile, social screens)
                           ► Sub-Plan 7 (Bundle pricing)
Sub-Plan 6 (Mobile) ──────► Sub-Plan 7 (screen time, location)
```

### Cross-Cutting Concerns (Apply to ALL Sub-Plans)

| Concern | Standard | Enforcement |
|---------|----------|-------------|
| Testing | TDD: write failing test first, then implement | CI blocks merge without tests |
| Security | OWASP Top 10, encrypted credentials, RBAC on all endpoints | Security test suite per module |
| Accessibility | WCAG 2.1 AA | `tsc --noEmit` + vitest + manual check |
| i18n | 6 languages (EN, FR, ES, DE, PT-BR, IT) | All user-facing strings in `portal/messages/` |
| Logging | `structlog.get_logger()` with correlation IDs | Never `print()` |
| Errors | `BhapiException` subclasses only | Never raw `HTTPException` |
| Commits | Frequent, small, descriptive | One logical change per commit |
| Code quality | Ruff (100 char line), strict TypeScript | CI enforces |
| Documentation | Update CLAUDE.md when adding modules/routes | Part of Definition of Done |

---

## Sub-Plan 1: COPPA 2026 Compliance

**Deadline: April 22, 2026 (36 days from today)**
**Effort: 4-5 person-weeks**
**Risk if missed: FTC enforcement, fines up to $50,120 per violation**

### Context

The FTC's updated COPPA rule introduces 5 new requirements. The AI Portal has partial compliance (consent flows exist, COPPA dashboard exists, Yoti age verification integrated). Gaps: third-party consent not itemized, no written data retention policy, VPC needs strengthening, no "refuse partial collection" toggle, push notification consent not separated.

**IMPORTANT: Existing migration `031_coppa_2026.py` already creates tables:** `third_party_consent_items`, `retention_policies`, `push_notification_consents`, `video_verifications`. New work should build on these existing tables rather than creating duplicates. Review `alembic/versions/031_coppa_2026.py` before starting.

**Auth pattern for this codebase:** All routers use `GroupContext` from `src/schemas.py` with `get_current_user` from `src/auth/middleware.py`. DB sessions use the `DbSession` type alias from `src/dependencies.py`. There is no `AuthContext` or `require_permission` — role checks use `auth.role` and `auth.permissions` directly from `GroupContext`.

### Files

**Create:**
- `src/compliance/coppa_2026/` — New sub-module for COPPA 2026 specific logic
  - `__init__.py` — Public interface
  - `router.py` — COPPA 2026 endpoints (third-party consent, data retention disclosures)
  - `service.py` — Consent management, retention policy engine
  - `models.py` — SQLAlchemy models wrapping existing 031 tables + any new columns
  - `schemas.py` — Pydantic schemas for all COPPA 2026 flows
- `alembic/versions/032_*.py` — Migration for any new columns/tables not covered by 031 (auto-numbered by `alembic revision --autogenerate`)
- `tests/unit/test_coppa_2026.py` — Unit tests for consent logic
- `tests/e2e/test_coppa_2026_e2e.py` — E2E tests for full flows
- `tests/security/test_coppa_2026_security.py` — Auth/RBAC tests
- `portal/src/app/(dashboard)/compliance/coppa/page.tsx` — COPPA consent management UI
- `portal/src/hooks/use-coppa-consent.ts` — React Query hooks for COPPA APIs
- `docs/compliance/coppa-2026-security-program.md` — Written security program document
- `docs/compliance/data-retention-policy.md` — Data retention policy document

**Modify:**
- `src/compliance/router.py` — Register COPPA 2026 sub-router
- `src/compliance/__init__.py` — Export COPPA 2026 public interfaces
- `src/groups/service.py` — Add "refuse partial collection" toggle to group settings
- `src/groups/models.py` — Add `refuse_third_party_sharing` column
- `src/groups/schemas.py` — Add field to group settings schema
- `src/auth/router.py` — Integrate VPC enhancement into registration flow
- `src/integrations/router.py` — Yoti VPC integration for consent flow
- `src/alerts/service.py` — Push notification consent check before sending
- `src/main.py` — Register COPPA 2026 router
- `alembic/env.py` — Import new COPPA 2026 models
- `portal/messages/en.json` (+ 5 other languages) — COPPA consent UI strings
- `src/legal/router.py` — Serve updated privacy policy with retention disclosures

---

### Task 1.1: Third-Party Data Flow Audit & Disclosure Model

**Files:**
- Create: `src/compliance/coppa_2026/__init__.py`
- Create: `src/compliance/coppa_2026/models.py`
- Create: `src/compliance/coppa_2026/schemas.py`
- Create: `tests/unit/test_coppa_2026.py`

- [ ] **Step 1: Create COPPA 2026 sub-module directory**

```bash
mkdir -p src/compliance/coppa_2026
touch src/compliance/coppa_2026/__init__.py
```

- [ ] **Step 2: Write failing test for ThirdPartyConsent model**

```python
# tests/unit/test_coppa_2026.py
import pytest
from src.compliance.coppa_2026.models import ThirdPartyConsent, DataRetentionPolicy
from src.compliance.coppa_2026.schemas import ThirdPartyConsentCreate, ThirdPartyConsentResponse


class TestThirdPartyConsentModel:
    """COPPA 2026 requires separate consent for each third-party data recipient."""

    def test_third_party_consent_fields(self):
        """Model must track: group_id, third_party_name, purpose, data_categories, consented, consented_at."""
        from sqlalchemy import inspect
        mapper = inspect(ThirdPartyConsent)
        columns = {c.key for c in mapper.columns}
        required = {"id", "group_id", "third_party_name", "third_party_purpose",
                     "data_categories", "consented", "consented_at", "consented_by",
                     "created_at", "updated_at"}
        assert required.issubset(columns)

    def test_consent_create_schema_validates(self):
        """Schema must require third_party_name and purpose."""
        data = ThirdPartyConsentCreate(
            third_party_name="Stripe",
            third_party_purpose="Payment processing for subscription billing",
            data_categories=["email", "payment_method"],
        )
        assert data.third_party_name == "Stripe"

    def test_consent_create_rejects_empty_name(self):
        """Must reject empty third-party name."""
        with pytest.raises(Exception):
            ThirdPartyConsentCreate(
                third_party_name="",
                third_party_purpose="Something",
                data_categories=["email"],
            )
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/unit/test_coppa_2026.py -v`
Expected: FAIL with ImportError (module doesn't exist yet)

- [ ] **Step 4: Implement ThirdPartyConsent model and schemas**

```python
# src/compliance/coppa_2026/models.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from src.database import Base
from src.models import UUIDMixin, TimestampMixin


class ThirdPartyConsentItem(Base, UUIDMixin, TimestampMixin):
    """Wraps existing `third_party_consent_items` table from migration 031.
    Tracks per-third-party parental consent per COPPA 2026 Section 312.5(a)(2)."""
    __tablename__ = "third_party_consent_items"

    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True)
    member_id = Column(UUID(as_uuid=True), ForeignKey("group_members.id"), nullable=False)
    parent_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    provider_key = Column(String(50), nullable=False)
    provider_name = Column(String(100), nullable=False)
    data_purpose = Column(String(500), nullable=False)
    consented = Column(Boolean, nullable=False, default=False)
    consented_at = Column(DateTime(timezone=True), nullable=True)
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    ip_address = Column(String(45), nullable=True)


class RetentionPolicy(Base, UUIDMixin, TimestampMixin):
    """Wraps existing `retention_policies` table from migration 031.
    Documents data retention periods per COPPA 2026 Section 312.10."""
    __tablename__ = "retention_policies"

    data_category = Column(String(255), nullable=False, unique=True)
    purpose = Column(String(1000), nullable=False)
    retention_days = Column(Integer, nullable=False)
    deletion_method = Column(String(500), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
```

```python
# src/compliance/coppa_2026/schemas.py
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class ThirdPartyConsentCreate(BaseModel):
    third_party_name: str = Field(..., min_length=1, max_length=255)
    third_party_purpose: str = Field(..., min_length=1, max_length=1000)
    data_categories: list[str] = Field(..., min_length=1)

    @field_validator("third_party_name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Third-party name cannot be blank")
        return v.strip()


class ThirdPartyConsentResponse(BaseModel):
    id: UUID
    group_id: UUID
    third_party_name: str
    third_party_purpose: str
    data_categories: list[str]
    consented: bool
    consented_at: Optional[datetime] = None
    consented_by: Optional[UUID] = None

    model_config = {"from_attributes": True}


class DataRetentionPolicyResponse(BaseModel):
    data_category: str
    purpose: str
    retention_days: int
    deletion_method: str

    model_config = {"from_attributes": True}
```

```python
# src/compliance/coppa_2026/__init__.py
from src.compliance.coppa_2026.models import ThirdPartyConsent, DataRetentionPolicy
from src.compliance.coppa_2026.schemas import (
    ThirdPartyConsentCreate,
    ThirdPartyConsentResponse,
    DataRetentionPolicyResponse,
)

__all__ = [
    "ThirdPartyConsent",
    "DataRetentionPolicy",
    "ThirdPartyConsentCreate",
    "ThirdPartyConsentResponse",
    "DataRetentionPolicyResponse",
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_coppa_2026.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add src/compliance/coppa_2026/ tests/unit/test_coppa_2026.py
git commit -m "feat(coppa): add ThirdPartyConsent and DataRetentionPolicy models for COPPA 2026"
```

---

### Task 1.2: Third-Party Consent Service & Router

**Files:**
- Create: `src/compliance/coppa_2026/service.py`
- Create: `src/compliance/coppa_2026/router.py`
- Create: `tests/e2e/test_coppa_2026_e2e.py`
- Modify: `src/main.py` — Register router
- Modify: `alembic/env.py` — Import models

- [ ] **Step 1: Write failing E2E test for third-party consent listing**

```python
# tests/e2e/test_coppa_2026_e2e.py
import pytest
from httpx import AsyncClient


class TestThirdPartyConsentAPI:
    """COPPA 2026: Parents must see and manage per-third-party consent."""

    @pytest.mark.asyncio
    async def test_list_third_party_disclosures(self, client: AsyncClient, auth_headers: dict):
        """GET /api/v1/compliance/coppa/third-parties returns all third parties."""
        response = await client.get("/api/v1/compliance/coppa/third-parties", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Platform should have pre-seeded third parties (Stripe, SendGrid, etc.)

    @pytest.mark.asyncio
    async def test_grant_consent_for_third_party(self, client: AsyncClient, auth_headers: dict):
        """POST /api/v1/compliance/coppa/third-parties/{id}/consent grants consent."""
        # First get the list
        response = await client.get("/api/v1/compliance/coppa/third-parties", headers=auth_headers)
        parties = response.json()
        if parties:
            party_id = parties[0]["id"]
            response = await client.post(
                f"/api/v1/compliance/coppa/third-parties/{party_id}/consent",
                headers=auth_headers,
            )
            assert response.status_code == 200
            assert response.json()["consented"] is True

    @pytest.mark.asyncio
    async def test_revoke_consent_for_third_party(self, client: AsyncClient, auth_headers: dict):
        """DELETE /api/v1/compliance/coppa/third-parties/{id}/consent revokes consent."""
        response = await client.get("/api/v1/compliance/coppa/third-parties", headers=auth_headers)
        parties = response.json()
        if parties:
            party_id = parties[0]["id"]
            # Grant first
            await client.post(
                f"/api/v1/compliance/coppa/third-parties/{party_id}/consent",
                headers=auth_headers,
            )
            # Then revoke
            response = await client.delete(
                f"/api/v1/compliance/coppa/third-parties/{party_id}/consent",
                headers=auth_headers,
            )
            assert response.status_code == 200
            assert response.json()["consented"] is False

    @pytest.mark.asyncio
    async def test_refuse_partial_collection_toggle(self, client: AsyncClient, auth_headers: dict):
        """PATCH /api/v1/groups/{id}/settings can set refuse_third_party_sharing."""
        # This tests the "right to refuse partial collection" COPPA requirement
        pass  # Will be implemented in Task 1.3

    @pytest.mark.asyncio
    async def test_data_retention_disclosures(self, client: AsyncClient, auth_headers: dict):
        """GET /api/v1/compliance/coppa/data-retention returns retention policies."""
        response = await client.get("/api/v1/compliance/coppa/data-retention", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Each policy must have: data_category, purpose, retention_days, deletion_method
        for policy in data:
            assert "data_category" in policy
            assert "retention_days" in policy
            assert policy["retention_days"] > 0


class TestThirdPartyConsentSecurity:
    """Auth and RBAC tests for COPPA consent endpoints."""

    @pytest.mark.asyncio
    async def test_unauthenticated_rejected(self, client: AsyncClient):
        response = await client.get("/api/v1/compliance/coppa/third-parties")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_child_member_cannot_manage_consent(self, client: AsyncClient, child_headers: dict):
        """Only parents/admins can manage consent, not child members."""
        response = await client.get("/api/v1/compliance/coppa/third-parties", headers=child_headers)
        # Child should be able to view but not modify
        # Exact behavior depends on role implementation
        assert response.status_code in (200, 403)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/e2e/test_coppa_2026_e2e.py -v`
Expected: FAIL (no router registered)

- [ ] **Step 3: Implement service and router**

```python
# src/compliance/coppa_2026/service.py
import structlog
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.compliance.coppa_2026.models import ThirdPartyConsent, DataRetentionPolicy
from src.compliance.coppa_2026.schemas import ThirdPartyConsentCreate
from src.exceptions import NotFoundError

logger = structlog.get_logger()

# Pre-defined third parties that Bhapi shares data with
PLATFORM_THIRD_PARTIES = [
    ThirdPartyConsentCreate(
        third_party_name="Stripe",
        third_party_purpose="Payment processing for subscription billing",
        data_categories=["email", "name", "payment_method"],
    ),
    ThirdPartyConsentCreate(
        third_party_name="SendGrid",
        third_party_purpose="Transactional email delivery (alerts, reports, verification)",
        data_categories=["email", "name"],
    ),
    ThirdPartyConsentCreate(
        third_party_name="Twilio",
        third_party_purpose="SMS alert delivery",
        data_categories=["phone_number"],
    ),
    ThirdPartyConsentCreate(
        third_party_name="Hive AI",
        third_party_purpose="Deepfake detection analysis (when enabled)",
        data_categories=["content_metadata"],
    ),
    ThirdPartyConsentCreate(
        third_party_name="Sensity AI",
        third_party_purpose="Deepfake detection analysis (when enabled)",
        data_categories=["content_metadata"],
    ),
    ThirdPartyConsentCreate(
        third_party_name="Yoti",
        third_party_purpose="Age verification for parental consent",
        data_categories=["facial_image", "date_of_birth"],
    ),
]


async def get_third_party_consents(db: AsyncSession, group_id: UUID) -> list[ThirdPartyConsent]:
    """Get all third-party consent records for a group."""
    result = await db.execute(
        select(ThirdPartyConsent)
        .where(ThirdPartyConsent.group_id == group_id)
        .order_by(ThirdPartyConsent.third_party_name)
    )
    return list(result.scalars().all())


async def ensure_third_party_records(db: AsyncSession, group_id: UUID) -> list[ThirdPartyConsent]:
    """Ensure all platform third parties have consent records for this group."""
    existing = await get_third_party_consents(db, group_id)
    existing_names = {c.third_party_name for c in existing}

    for tp in PLATFORM_THIRD_PARTIES:
        if tp.third_party_name not in existing_names:
            consent = ThirdPartyConsent(
                group_id=group_id,
                third_party_name=tp.third_party_name,
                third_party_purpose=tp.third_party_purpose,
                data_categories=tp.data_categories,
                consented=False,
            )
            db.add(consent)

    await db.flush()
    return await get_third_party_consents(db, group_id)


async def grant_consent(db: AsyncSession, consent_id: UUID, user_id: UUID) -> ThirdPartyConsent:
    """Grant consent for a specific third party."""
    consent = await db.get(ThirdPartyConsent, consent_id)
    if not consent:
        raise NotFoundError("Third-party consent record not found")
    consent.consented = True
    consent.consented_at = datetime.now(timezone.utc)
    consent.consented_by = user_id
    consent.revoked_at = None
    await db.flush()
    await db.refresh(consent)
    logger.info("coppa_consent_granted", third_party=consent.third_party_name, group_id=str(consent.group_id))
    return consent


async def revoke_consent(db: AsyncSession, consent_id: UUID) -> ThirdPartyConsent:
    """Revoke consent for a specific third party."""
    consent = await db.get(ThirdPartyConsent, consent_id)
    if not consent:
        raise NotFoundError("Third-party consent record not found")
    consent.consented = False
    consent.revoked_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(consent)
    logger.info("coppa_consent_revoked", third_party=consent.third_party_name, group_id=str(consent.group_id))
    return consent


async def get_data_retention_policies(db: AsyncSession) -> list[DataRetentionPolicy]:
    """Get all active data retention policies."""
    result = await db.execute(
        select(DataRetentionPolicy)
        .where(DataRetentionPolicy.is_active.is_(True))
        .order_by(DataRetentionPolicy.data_category)
    )
    return list(result.scalars().all())
```

```python
# src/compliance/coppa_2026/router.py
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.dependencies import DbSession
from src.auth.middleware import get_current_user
from src.schemas import GroupContext
from src.compliance.coppa_2026 import service, schemas

router = APIRouter(prefix="/api/v1/compliance/coppa", tags=["coppa-2026"])


@router.get("/third-parties", response_model=list[schemas.ThirdPartyConsentResponse])
async def list_third_party_consents(
    auth: GroupContext = Depends(get_current_user),
    db: DbSession,
):
    """List all third-party data recipients and their consent status."""
    return await service.ensure_third_party_records(db, auth.group_id)


@router.post("/third-parties/{consent_id}/consent", response_model=schemas.ThirdPartyConsentResponse)
async def grant_third_party_consent(
    consent_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: DbSession,
):
    """Grant consent for data sharing with a specific third party."""
    if auth.role not in ("owner", "admin"):
        from src.exceptions import ForbiddenError
        raise ForbiddenError("Only group owners/admins can manage consent")
    return await service.grant_consent(db, consent_id, auth.user_id)


@router.delete("/third-parties/{consent_id}/consent", response_model=schemas.ThirdPartyConsentResponse)
async def revoke_third_party_consent(
    consent_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: DbSession,
):
    """Revoke consent for data sharing with a specific third party."""
    if auth.role not in ("owner", "admin"):
        from src.exceptions import ForbiddenError
        raise ForbiddenError("Only group owners/admins can manage consent")
    return await service.revoke_consent(db, consent_id)


@router.get("/data-retention", response_model=list[schemas.DataRetentionPolicyResponse])
async def get_data_retention_policies(
    auth: GroupContext = Depends(get_current_user),
    db: DbSession,
):
    """Get data retention policies (COPPA 2026 requires these be disclosed to parents)."""
    return await service.get_data_retention_policies(db)
```

- [ ] **Step 4: Create Alembic migration**

Run: `alembic revision --autogenerate -m "coppa_2026_third_party_consent_and_retention"`
Verify: `git status` shows new migration file

- [ ] **Step 5: Register router in main.py and import models in alembic/env.py**

Add to `src/main.py`:
```python
from src.compliance.coppa_2026.router import router as coppa_2026_router
app.include_router(coppa_2026_router)
```

Add to `alembic/env.py`:
```python
from src.compliance.coppa_2026.models import ThirdPartyConsent, DataRetentionPolicy
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/e2e/test_coppa_2026_e2e.py tests/unit/test_coppa_2026.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/compliance/coppa_2026/ tests/ alembic/ src/main.py
git commit -m "feat(coppa): third-party consent management and data retention disclosure APIs"
```

---

### Task 1.3: Refuse Partial Collection Toggle

**Files:**
- Modify: `src/groups/models.py` — Add `refuse_third_party_sharing` column
- Modify: `src/groups/schemas.py` — Add field
- Modify: `src/groups/service.py` — Enforce toggle
- Create: `alembic/versions/032_refuse_partial_collection.py` (or next auto-numbered)

- [ ] **Step 1: Write failing test**

```python
# Add to tests/e2e/test_coppa_2026_e2e.py
class TestRefusePartialCollection:
    """COPPA 2026: Parents can consent to collection but refuse third-party sharing."""

    @pytest.mark.asyncio
    async def test_toggle_refuse_third_party_sharing(self, client: AsyncClient, auth_headers: dict, test_group_id: str):
        response = await client.patch(
            f"/api/v1/groups/{test_group_id}/settings",
            json={"refuse_third_party_sharing": True},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["refuse_third_party_sharing"] is True

    @pytest.mark.asyncio
    async def test_refuse_blocks_all_non_integral_sharing(self, client: AsyncClient, auth_headers: dict, test_group_id: str):
        """When refuse is on, all non-integral third-party consents are revoked."""
        # Enable refuse
        await client.patch(
            f"/api/v1/groups/{test_group_id}/settings",
            json={"refuse_third_party_sharing": True},
            headers=auth_headers,
        )
        # Check consents are all revoked (except integral ones like Stripe for billing)
        response = await client.get("/api/v1/compliance/coppa/third-parties", headers=auth_headers)
        consents = response.json()
        # Non-integral third parties should have consented=False
        non_integral = [c for c in consents if c["third_party_name"] not in ("Stripe",)]
        for c in non_integral:
            assert c["consented"] is False
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Add column to Group model, update schema, update service**
- [ ] **Step 4: Create Alembic migration**

Run: `alembic revision --autogenerate -m "add_refuse_third_party_sharing_to_groups"`

- [ ] **Step 5: Run tests to verify they pass**
- [ ] **Step 6: Commit**

---

### Task 1.4: VPC Enhancement (Verifiable Parental Consent)

**Files:**
- Modify: `src/auth/router.py` — Add VPC verification step to registration
- Modify: `src/integrations/` — Yoti integration for facial match VPC
- Create: `tests/e2e/test_vpc_e2e.py`

- [ ] **Step 1: Write failing test for SMS + confirmation VPC method**

The simplest COPPA-compliant VPC method to implement is SMS + confirmation text:
1. Send SMS to parent's phone
2. Parent replies with confirmation code
3. System records verified consent

```python
# tests/e2e/test_vpc_e2e.py
class TestVPCEnhancement:
    """COPPA 2026: Knowledge-based methods no longer sufficient."""

    @pytest.mark.asyncio
    async def test_sms_vpc_initiate(self, client: AsyncClient, auth_headers: dict):
        """POST /api/v1/auth/vpc/initiate sends verification SMS."""
        response = await client.post(
            "/api/v1/auth/vpc/initiate",
            json={"phone_number": "+15551234567", "method": "sms"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["verification_id"] is not None

    @pytest.mark.asyncio
    async def test_sms_vpc_verify(self, client: AsyncClient, auth_headers: dict):
        """POST /api/v1/auth/vpc/verify confirms consent."""
        response = await client.post(
            "/api/v1/auth/vpc/verify",
            json={"verification_id": "test-id", "code": "123456"},
            headers=auth_headers,
        )
        # In test mode, should accept test codes
        assert response.status_code in (200, 422)
```

- [ ] **Step 2-6: Implement, test, commit** (standard TDD cycle)

---

### Task 1.5: Push Notification Consent

**Files:**
- Modify: `src/alerts/service.py` — Check push consent before sending
- Modify: `src/alerts/models.py` — Add `push_consent` field
- Modify: `src/groups/models.py` — Add `push_notification_consent` to group settings
- Modify: existing `push_notification_consents` table from migration 031 (add columns if needed)

- [ ] **Step 1-6: TDD cycle** — Migration 031 already created `push_notification_consents` table with per-member, per-notification-type consent tracking. Build the service layer and router to manage these records, and modify `src/alerts/service.py` to check consent before sending push notifications containing child data.

---

### Task 1.6: Written Security Program & Data Retention Policy Documents

**Files:**
- Create: `docs/compliance/coppa-2026-security-program.md`
- Create: `docs/compliance/data-retention-policy.md`
- Modify: `src/legal/router.py` — Serve retention policy via API
- Create: data seed script for DataRetentionPolicy records

- [ ] **Step 1: Write COPPA-formatted security program document**

Must include: designated responsible person, safeguards proportionate to data sensitivity, annual review commitment, risk assessment schedule.

- [ ] **Step 2: Write data retention policy**

| Data Category | Retention Period | Purpose | Deletion Method |
|---|---|---|---|
| Conversation captures | 90 days | AI safety monitoring | Secure deletion |
| Risk scores | 1 year | Trend analysis | Soft delete + purge |
| Alert history | 1 year | Safety record | Soft delete + purge |
| Account data | Duration of account + 30 days | Service delivery | Full deletion |
| Billing data | 7 years | Legal/tax requirement | Archive + restrict |
| Consent records | 3 years after revocation | Compliance audit trail | Archive |
| Extension telemetry | 30 days | Performance monitoring | Auto-purge |

- [ ] **Step 3: Seed DataRetentionPolicy records via migration**
- [ ] **Step 4: Update legal router to serve retention disclosures**
- [ ] **Step 5: Commit**

---

### Task 1.7: COPPA 2026 Frontend — Consent Management UI

**Files:**
- Create: `portal/src/app/(dashboard)/compliance/coppa/page.tsx`
- Create: `portal/src/hooks/use-coppa-consent.ts`
- Modify: `portal/messages/en.json` (+ 5 languages)
- Create: `portal/src/__tests__/coppa-consent.test.tsx`

- [ ] **Step 1: Write vitest test for consent management page**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement page with third-party list, consent toggles, retention disclosures**
- [ ] **Step 4: Add i18n strings to all 6 language files**
- [ ] **Step 5: Run `npx tsc --noEmit` and `npx vitest run`**
- [ ] **Step 6: Commit**

---

### Task 1.8: COPPA 2026 Integration Test Suite

**Files:**
- Create: `tests/security/test_coppa_2026_security.py`
- Modify: `tests/e2e/test_coppa_2026_e2e.py` — Expand with full flow tests

- [ ] **Step 1: Write security tests** (auth required, RBAC enforced, child members can't modify consent)
- [ ] **Step 2: Write full-flow E2E test** (register → VPC → consent management → refuse partial → verify enforcement)
- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All existing tests still pass + new COPPA tests pass

- [ ] **Step 4: Commit**

---

## Sub-Plan 2: Legacy Security Triage & Archival Decision

**Effort: 2-3 person-weeks**
**Dependency: None (can run in parallel with Sub-Plan 1)**

### Context

The three `bhapi-inc` repositories (bhapi-api, bhapi-mobile, back-office) have 0 tests, 18 unmerged Snyk PRs, and critical security vulnerabilities. Per ADR-005, these repos will be archived. However, we need to: (1) make the archival decision formally, (2) extract any useful reference material, (3) ensure no users are left on broken systems.

**Gap analysis items superseded by this approach:**
- **A-C1 (Security Hardening, 6-8 pw):** Reduced to triage + archival since legacy code is not carried forward
- **A-C2 (React Native Upgrade, 8-12 pw):** Superseded by ADR-004 (greenfield Expo SDK 52+)
- **A-C3 (Test Coverage 0→baseline, 12-17 pw):** Superseded by ADR-004/005 (archived, not maintained)
- **A-H5 (Back-Office Security Fixes, 3-4 pw):** Only relevant if App remains online; otherwise superseded by archival

### Task 2.1: Security Audit of Legacy Repos

- [ ] **Step 1: Review all 18 Snyk PRs across the 3 repos**

Run (for each repo):
```bash
gh pr list --repo bhapi-inc/bhapi-api --state open --label "Snyk"
gh pr list --repo bhapi-inc/bhapi-mobile --state open --label "Snyk"
gh pr list --repo bhapi-inc/back-office --state open --label "Snyk"
```

Document: Which vulnerabilities are actively exploitable? Which are theoretical?

- [ ] **Step 2: Document current user base and data exposure**

Questions to answer:
- How many active users does the Bhapi App have?
- Is the bhapi-api currently serving production traffic?
- Is MongoDB storing child PII?
- What data would need to be migrated vs deleted?

- [ ] **Step 3: Make go/no-go decision on App**

Decision matrix:
| Condition | Action |
|---|---|
| Active users + exploitable vulns | Take offline immediately, notify users, plan migration |
| Active users + no exploitable vulns | Merge Snyk PRs, set deprecation timeline |
| No active users | Archive immediately per ADR-005 |

- [ ] **Step 4: Commit decision document**

---

### Task 2.2: Archive Legacy Repositories

**Clean break:** The unified platform is built fresh with no connection to the current bhapi.com app or portal.bhapi.com. No user migration, no data migration, no MongoDB ETL. The legacy repos serve as **feature reference only** — we study what they do and rebuild the features properly in the unified platform. User migration from bhapi.com can happen later as a separate initiative if needed.

- [ ] **Step 1: Add deprecation notice to each repo's README**

```markdown
# DEPRECATED — This repository has been archived

This project has been superseded by the [Bhapi Platform](https://github.com/mick-e/bhapi-platform).
All active development, including social features, AI safety monitoring, and mobile apps,
now lives in the unified Bhapi Platform repository.

For migration information, see [ADR-005: Platform Unification](link).
```

- [ ] **Step 2: Archive each repo on GitHub**

```bash
gh repo archive bhapi-inc/bhapi-api --yes
gh repo archive bhapi-inc/bhapi-mobile --yes
gh repo archive bhapi-inc/back-office --yes
```

- [ ] **Step 3: Extract reference material**

Copy functional reference docs from legacy repos into `docs/legacy-reference/`:
- API endpoint inventory from bhapi-api
- Screen inventory from bhapi-mobile (43 screens, 29 components)
- RBAC role definitions from back-office
- Google Cloud AI integration patterns from bhapi-api

- [ ] **Step 4: Commit reference docs**

---

### Task 2.3: Extract Feature Reference from Legacy Repos

- [ ] **Step 1: Document bhapi-api endpoints** — Map all ~30 REST API endpoints, request/response shapes, moderation workflows, Google Cloud AI integration patterns
- [ ] **Step 2: Document bhapi-mobile screens** — Screenshot and catalog all 43 screens, 29 components, navigation flow, social features
- [ ] **Step 3: Document back-office features** — Catalog portal.bhapi.com pages (Accounts, Posts, Organizations, Support, Settings), RBAC roles (super-admin, admin, moderator, support), workflows
- [ ] **Step 4: Save reference docs to `docs/legacy-reference/`**
- [ ] **Step 5: Commit**

---

## Sub-Plan 3: Platform Unification Foundation

**Effort: 3-4 person-weeks**
**Dependencies: Sub-Plan 2 (archival decision)**

### Context

Per ADR-005, rename `bhapi-ai-portal` to `bhapi-platform`, update all branding, establish the unified codebase structure for social features (ADR-002), and prepare for mobile app (ADR-004).

### Task 3.1: Repository Rename & Brand Update

- [ ] **Step 1: Rename GitHub repository**

```bash
gh repo rename bhapi-platform --repo mick-e/bhapi-ai-portal
```

GitHub handles redirects automatically.

- [ ] **Step 2: Update all internal references**

Files to update:
- `render.yaml` — service name
- `.github/workflows/ci.yml` — repo name in any references
- `CLAUDE.md` — project name
- `portal/package.json` — package name
- `docker-compose.yml` — service names
- `Dockerfile` — any repo-specific references
- `docs/` — all references to "AI Portal" → "Bhapi Platform"

- [ ] **Step 3: Update CLAUDE.md header**

Change "Bhapi Family AI Governance Portal" to "Bhapi Platform" and add social module section.

- [ ] **Step 4: Commit**

---

### Task 3.2: Social Module Directory Structure (ADR-002)

**Files:**
- Create: `src/social/__init__.py`
- Create: `src/social/posts/` (router, service, models, schemas)
- Create: `src/social/comments/` (router, service, models, schemas)
- Create: `src/social/followers/` (router, service, models, schemas)
- Create: `src/social/messaging/` (router, service, models, schemas)
- Create: `src/social/search/` (router, service, schemas)
- Create: `src/social/moderation/` (shared content moderation hooks)

- [ ] **Step 1: Create directory structure with empty modules**

```bash
for module in posts comments followers messaging search moderation; do
    mkdir -p src/social/$module
    touch src/social/$module/__init__.py
    touch src/social/$module/router.py
    touch src/social/$module/service.py
    touch src/social/$module/models.py
    touch src/social/$module/schemas.py
done
```

- [ ] **Step 2: Define social permission strings**

Add social permission constants to `src/social/__init__.py` (the codebase uses string-based permissions in `GroupContext.permissions`, not a separate permissions module):
```python
# src/social/__init__.py
# Social permission strings — checked via `if perm in auth.permissions`
SOCIAL_POST_CREATE = "social:post:create"
SOCIAL_POST_MODERATE = "social:post:moderate"
SOCIAL_MESSAGE_SEND = "social:message:send"
SOCIAL_FOLLOW = "social:follow"
SOCIAL_SEARCH = "social:search"
```

- [ ] **Step 3: Commit scaffold**

---

### Task 3.3: Mobile App Scaffold (ADR-004)

**Files:**
- Create: `mobile/` directory at repo root
- Initialize Expo SDK 52+ project

- [ ] **Step 1: Initialize Expo project**

```bash
npx create-expo-app@latest mobile --template blank-typescript
cd mobile
npx expo install expo-secure-store expo-router @tanstack/react-query
```

- [ ] **Step 2: Configure TypeScript strict mode**

```json
// mobile/tsconfig.json
{
  "extends": "expo/tsconfig.base",
  "compilerOptions": {
    "strict": true,
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

- [ ] **Step 3: Set up secure token storage**

```typescript
// mobile/src/lib/auth.ts
import * as SecureStore from 'expo-secure-store';

const TOKEN_KEY = 'bhapi_auth_token';

export async function setToken(token: string): Promise<void> {
    await SecureStore.setItemAsync(TOKEN_KEY, token);
}

export async function getToken(): Promise<string | null> {
    return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function clearToken(): Promise<void> {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
}
```

- [ ] **Step 4: Add mobile/ to CI pipeline**
- [ ] **Step 5: Commit**

---

### Task 3.4: Unified Auth Extensions (ADR-001)

**Files:**
- Modify: `src/auth/router.py` — Add OAuth2 social login stubs
- Modify: `src/auth/service.py` — Add token refresh endpoint
- Create: `tests/e2e/test_unified_auth_e2e.py`

- [ ] **Step 1: Add refresh token support** (mobile apps need this; web uses cookies)
- [ ] **Step 2: Add OAuth2 stubs for Google/Apple sign-in** (social login needed for mobile)
- [ ] **Step 3: Test, commit**

---

## Sub-Plan 4: School Market Entry & EU AI Act Compliance

**Effort: 14-20 person-weeks (split across Phase 1 and Phase 2)**
**Dependencies: Sub-Plan 3 (platform foundation)**
**Deadlines: Ohio AI Mandate (Jul 1), EU AI Act (Aug 2)**

### Phase 1 Tasks (Weeks 6-12): School Market

### Task 4.1: Google Admin Console Integration for Extension Deployment

**Files:**
- Modify: `extension/manifest.json` — Chrome Web Store enterprise metadata
- Create: `docs/deployment/chromebook-admin-guide.md`
- Create: `src/integrations/google_admin/` — Google Admin SDK integration
- Create: `tests/e2e/test_google_admin_e2e.py`

- [ ] **Step 1: Update extension manifest for enterprise deployment**

Add `"update_url"` and enterprise policy fields to `extension/manifest.json`.

- [ ] **Step 2: Create Google Admin Console integration module**

Endpoints for:
- Mass extension deployment status
- Device inventory sync
- Policy management (which AI platforms to monitor per OU)
- User provisioning sync with Clever/ClassLink

- [ ] **Step 3: Build school IT admin dashboard pages**

```
portal/src/app/(dashboard)/school/deployment/page.tsx — Device deployment status
portal/src/app/(dashboard)/school/policies/page.tsx — AI monitoring policies
portal/src/app/(dashboard)/school/devices/page.tsx — Device inventory
```

- [ ] **Step 4: Chrome Web Store submission**
- [ ] **Step 5: Test, commit**

---

### Task 4.2: Ohio AI Governance Compliance Package

**Files:**
- Create: `src/compliance/governance/` — State AI governance module
  - `router.py` — Policy generator, compliance dashboard
  - `service.py` — Policy template engine
  - `models.py` — GovernancePolicy, GovernanceAudit
  - `schemas.py`
  - `templates/` — State-specific policy templates
- Create: `portal/src/app/(dashboard)/governance/page.tsx`
- Create: `tests/e2e/test_governance_e2e.py`

**First-mover opportunity: No competitor offers state-specific AI governance tools.**

- [ ] **Step 1: AI acceptable-use policy generator**

Build a template engine that generates school-specific AI policies based on:
- State requirements (Ohio HB provisions)
- District size and grade levels
- AI platforms in use (from monitoring data)
- Staff training requirements

- [ ] **Step 2: Compliance dashboard**

Show: policy status, last review date, AI tool inventory, training completion, audit trail.

- [ ] **Step 3: AI tool inventory and risk assessment**

Auto-populate from monitoring data: which AI platforms are students using, usage volume, risk scores.

- [ ] **Step 4: Compliance reporting for school boards**

PDF/CSV export formatted for school board presentations.

- [ ] **Step 5: Test, commit**

---

### Task 4.3: AI Platform Expansion (10 → 15+)

**Files:**
- Modify: `extension/` — Add platform detection for 5+ additional AI platforms
- Create: `extension/platforms/meta-ai.js`
- Create: `extension/platforms/mistral.js`
- Create: `extension/platforms/cohere.js`
- Create: `extension/platforms/llama.js`
- Create: `extension/platforms/deepseek.js`

- [ ] **Step 1: Add Meta AI, Mistral, Cohere, Llama (Meta), DeepSeek** detection to extension
- [ ] **Step 2: Update platform safety ratings**
- [ ] **Step 3: Test each platform detection**
- [ ] **Step 4: Update marketing materials / landing page**
- [ ] **Step 5: Commit**

---

### Phase 2 Tasks (Weeks 13-20): EU AI Act Compliance

### Task 4.4: EU AI Act Conformity Assessment

**Files:**
- Create: `src/compliance/eu_ai_act/` — EU AI Act compliance module
  - `router.py` — Conformity assessment, technical docs, risk management
  - `service.py` — Assessment logic, document generation
  - `models.py` — ConformityAssessment, RiskManagementRecord, BiasTestResult
  - `schemas.py`
- Create: `portal/src/app/(dashboard)/compliance/eu-ai-act/page.tsx`
- Create: `tests/e2e/test_eu_ai_act_e2e.py`

High-risk AI system requirements (Articles 9-15, 43, 49):

- [ ] **Step 1: Risk management system** (Art. 9) — Continuous risk identification dashboard
- [ ] **Step 2: Data governance** (Art. 10) — Bias testing framework with published results
- [ ] **Step 3: Technical documentation** (Art. 11) — Auto-generated from codebase metadata
- [ ] **Step 4: Accuracy & robustness** (Art. 15) — Performance benchmark dashboard
- [ ] **Step 5: Conformity assessment** (Art. 43) — Self-assessment questionnaire + document output
- [ ] **Step 6: EU database registration** (Art. 49) — Submit registration
- [ ] **Step 7: Test, commit**

---

## Sub-Plan 5: Social Module & Back-Office Admin Implementation

**Effort: 20-28 person-weeks**
**Dependencies: Sub-Plan 3 (scaffold), Sub-Plan 1 (COPPA compliance for child data)**

### Context

Build the social features (posts, comments, followers, messaging, search) AND the back-office admin features as modules in the unified FastAPI backend per ADR-002. All social content passes through the existing risk assessment engine for child safety. The old bhapi-api Express code and portal.bhapi.com back-office serve as functional reference only — no code is ported.

**Current live products being unified:**
- **bhapi.com social app** — Invitation-only safe social network. Parent master accounts, child sub-accounts. Live on [App Store](https://apps.apple.com/gb/app/bhapi/id1566061163) and [Play Store](https://play.google.com/store/apps/details?id=com.bhapi). Real users in MongoDB.
- **portal.bhapi.com back-office** — Internal admin dashboard for managing accounts, posts, organizations, support tickets, settings (analyzer thresholds, moderation config). 4 RBAC roles: super-admin, admin, moderator, support.

**Account model mapping (social app → AI portal):**
| Social App (bhapi.com) | AI Portal (bhapi.ai) | Status |
|---|---|---|
| Organization | Group | Already exists |
| Parent account (master) | Group owner | Already exists |
| Child sub-accounts | Group members (child role) | Already exists (cap: 5) |
| Invitation-only registration | Group invitations | Already exists |
| Account status (Active/Invited) | Member status | Already exists |

The AI portal's group/member model already provides the right primitives. Social features plug into this existing account structure.

### Task 5.1: Posts Module

**Files:**
- Implement: `src/social/posts/models.py` — Post, PostLike, PostMedia
- Implement: `src/social/posts/schemas.py` — PostCreate, PostResponse, FeedResponse
- Implement: `src/social/posts/service.py` — CRUD, feed algorithm, content moderation hook
- Implement: `src/social/posts/router.py` — POST/GET/DELETE /api/v1/social/posts
- Create: Alembic migration for social posts tables (auto-numbered via `alembic revision --autogenerate`)
- Create: `tests/unit/test_social_posts.py`
- Create: `tests/e2e/test_social_posts_e2e.py`
- Create: `tests/security/test_social_posts_security.py`

Key design decisions:
- Posts go through `src/risk/service.py` for safety scoring before publishing
- Posts with risk score > threshold are held for moderation
- Age-appropriate content filtering based on member age tier
- Soft-delete with `SoftDeleteMixin`
- Paginated response uses `PaginatedResponse` from `src/schemas.py`: `{items, total, offset, limit, has_more}`

**Core models (implement in `src/social/posts/models.py`):**

```python
class Post(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "social_posts"
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    content_type = Column(String(20), nullable=False, default="text")  # text, image, video
    media_url = Column(String(1000), nullable=True)
    risk_score = Column(Integer, nullable=True)  # From risk engine, 0-100
    moderation_status = Column(String(20), nullable=False, default="approved")  # approved, pending, rejected
    like_count = Column(Integer, nullable=False, default=0)
    comment_count = Column(Integer, nullable=False, default=0)

class PostLike(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "social_post_likes"
    post_id = Column(UUID(as_uuid=True), ForeignKey("social_posts.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    __table_args__ = (UniqueConstraint("post_id", "user_id"),)
```

**Core API routes:**
- `POST /api/v1/social/posts` — Create post (requires `social:post:create` permission)
- `GET /api/v1/social/posts` — Feed (paginated, filtered by group/user/age-tier)
- `GET /api/v1/social/posts/{id}` — Single post
- `DELETE /api/v1/social/posts/{id}` — Delete own post (soft-delete)
- `POST /api/v1/social/posts/{id}/like` — Like/unlike toggle

- [ ] **Steps 1-8: Full TDD cycle** (model → schema → service → router → E2E → security → commit)

---

### Task 5.2: Comments Module

**Files:** `src/social/comments/` — Threaded comments with reactions, moderation hooks

- [ ] **Steps 1-8: Full TDD cycle**

---

### Task 5.3: Followers Module

**Files:** `src/social/followers/` — Follow/unfollow, follower lists, privacy controls

- [ ] **Steps 1-8: Full TDD cycle**

Key: Parent-approved contacts for younger users (COPPA), age-tier restrictions

---

### Task 5.4: Messaging Module

**Files:** `src/social/messaging/` — Conversations, messages, WebSocket real-time delivery

**Core models (implement in `src/social/messaging/models.py`):**

```python
class Conversation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "social_conversations"
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False)
    conversation_type = Column(String(20), nullable=False, default="direct")  # direct, group
    last_message_at = Column(DateTime(timezone=True), nullable=True)

class ConversationParticipant(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "social_conversation_participants"
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("social_conversations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    last_read_at = Column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint("conversation_id", "user_id"),)

class Message(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "social_messages"
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("social_conversations.id"), nullable=False, index=True)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content_encrypted = Column(Text, nullable=False)  # Encrypted via encrypt_credential()
    risk_score = Column(Integer, nullable=True)
    moderation_status = Column(String(20), nullable=False, default="approved")
```

**Core API routes:**
- `GET /api/v1/social/messages/conversations` — List conversations
- `POST /api/v1/social/messages/conversations` — Start conversation
- `GET /api/v1/social/messages/conversations/{id}` — Get messages (paginated)
- `POST /api/v1/social/messages/conversations/{id}` — Send message
- `WS /api/v1/social/messages/ws` — WebSocket for real-time delivery

- [ ] **Steps 1-10: Full TDD cycle** — Including WebSocket tests

Key: Messages encrypted at rest via `encrypt_credential()`. Parent-approved contacts for under-13.

---

### Task 5.5: Social Search Module

**Files:** `src/social/search/` — PostgreSQL FTS for users, posts, hashtags

- [ ] **Steps 1-6: Full TDD cycle**

Reuse existing FTS infrastructure (`to_tsvector/plainto_tsquery` with GIN indexes).

---

### Task 5.6: Content Moderation Integration

**Files:**
- Implement: `src/social/moderation/service.py` — Hook into `src/risk/` for all social content
- Implement: `src/social/moderation/router.py` — Moderation queue for flagged content

All social content (posts, comments, messages) must pass through:
1. Text safety classification (existing 14-category risk taxonomy)
2. Image moderation (if media attached)
3. Age-appropriate content check
4. Profanity filter

- [ ] **Steps 1-6: Full TDD cycle**

---

### Task 5.7: Back-Office Admin Module (Replaces portal.bhapi.com)

**Files:**
- Create: `src/admin/` — Admin module for internal back-office management
  - `__init__.py` — Public interface
  - `router.py` — Admin API endpoints
  - `service.py` — Admin business logic
  - `schemas.py` — Admin-specific schemas
- Create: `portal/src/app/(dashboard)/admin/accounts/page.tsx` — Account management (replaces portal.bhapi.com/office/accounts)
- Create: `portal/src/app/(dashboard)/admin/posts/page.tsx` — Post moderation queue (replaces portal.bhapi.com Posts)
- Create: `portal/src/app/(dashboard)/admin/organizations/page.tsx` — Organization management
- Create: `portal/src/app/(dashboard)/admin/support/page.tsx` — Support ticket management
- Create: `portal/src/app/(dashboard)/admin/settings/page.tsx` — Analyzer thresholds, moderation config
- Create: `portal/src/hooks/use-admin.ts` — React Query hooks for admin APIs
- Create: `tests/e2e/test_admin_e2e.py`
- Create: `tests/security/test_admin_security.py`

**Admin features from portal.bhapi.com to rebuild:**

1. **Accounts page** (`/admin/accounts`)
   - List all users with: name, email, status (Active/Invited), sub-account count
   - Organization-scoped view (filter by group)
   - "Add or Import Accounts" — invite by email, bulk CSV import
   - Detail view: parent account + linked child sub-accounts
   - Activate/deactivate accounts, resend invitations
   - Search and status filter (All/Active/Invited/Suspended)

2. **Posts page** (`/admin/posts`)
   - Content moderation queue: published, blocked, reported posts
   - Bulk actions: approve, block, delete
   - Post detail view with risk score from AI safety engine
   - Moderator notes and action history
   - Filter by severity, platform, date range

3. **Organizations page** (`/admin/organizations`)
   - List all groups/organizations
   - Create/edit organizations
   - Member count, subscription status
   - Organization settings management

4. **Support page** (`/admin/support`)
   - Support ticket CRUD
   - Ticket assignment to staff
   - Status tracking (open, in-progress, resolved, closed)
   - User communication history

5. **Settings page** (`/admin/settings`)
   - Toxicity analyzer thresholds (Perspective API sensitivity)
   - Content moderation auto-actions (auto-block above threshold)
   - Email template editor
   - Platform-wide settings

**RBAC:** Admin pages gated by role — only `super-admin`, `admin`, `moderator`, `support` roles can access. Each role sees different pages:
- `super-admin`: All pages
- `admin`: Accounts, Posts, Organizations, Settings
- `moderator`: Posts (moderation queue only)
- `support`: Support, Accounts (read-only)

- [ ] **Step 1: Write failing tests for admin account listing API**

```python
# tests/e2e/test_admin_e2e.py
class TestAdminAccountsAPI:
    @pytest.mark.asyncio
    async def test_list_accounts_requires_admin_role(self, client, auth_headers):
        response = await client.get("/api/v1/admin/accounts", headers=auth_headers)
        # Regular users should be forbidden
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_accounts_as_admin(self, client, admin_headers):
        response = await client.get("/api/v1/admin/accounts", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        for account in data["items"]:
            assert "name" in account
            assert "email" in account
            assert "status" in account
            assert "sub_account_count" in account
```

- [ ] **Step 2-4: Implement admin router, service, and schemas (TDD cycle)**
- [ ] **Step 5: Write security tests** (RBAC enforcement for all 4 roles)
- [ ] **Step 6: Build admin frontend pages**
- [ ] **Step 7: Run `npx tsc --noEmit` and `npx vitest run`**
- [ ] **Step 8: Commit**

---

### Task 5.8: Social Frontend Pages

**Files:**
- Create: `portal/src/app/(dashboard)/social/feed/page.tsx` — Social feed
- Create: `portal/src/app/(dashboard)/social/messages/page.tsx` — Messaging
- Create: `portal/src/app/(dashboard)/social/profile/page.tsx` — User profile
- Create: `portal/src/app/(dashboard)/social/search/page.tsx` — Social search
- Create: `portal/src/hooks/use-social.ts` — React Query hooks for social APIs
- Create: `portal/src/__tests__/social-feed.test.tsx`
- Update: `portal/messages/*.json` — Social i18n strings

- [ ] **Steps 1-8: Component development with vitest + tsc**

---

## Sub-Plan 6: Mobile App & Device Agent

**Effort: 16-22 person-weeks**
**Dependencies: Sub-Plan 3 (mobile scaffold), Sub-Plan 5 (social APIs), Sub-Plan 1 (COPPA)**

### Context

Greenfield Expo SDK 52+ mobile app per ADR-004. This is the **single unified Bhapi mobile app** that replaces the current bhapi.com apps on [App Store](https://apps.apple.com/gb/app/bhapi/id1566061163) and [Play Store](https://play.google.com/store/apps/details?id=com.bhapi). ALL Bhapi features in one app:

1. **Parent experience** — AI safety dashboard, alerts, consent management, screen time controls, location tracking, social activity monitoring, content moderation approvals, family agreement management
2. **Child experience** — Social feed (posts, likes, comments), messaging (parent-approved contacts), profiles, AI safety status (age-appropriate view), panic button, rewards, AI literacy modules
3. **Device agent** — Background AI platform monitoring (native app conversations that browser extension can't capture), notification capture, usage tracking

**Registration model carried forward:** Invitation-only. Parents create master accounts, children get sub-accounts. Same model as current bhapi.com app, now built on the AI portal's group/member system.

**App Store:** New unified app published as a fresh listing. No connection to the current bhapi.com App Store / Play Store apps. The legacy apps remain as-is until manually sunset. User migration from old app is a separate future initiative.

### Task 6.1: Mobile App Core (Auth, Navigation, Theme)

**Design source:** This is a NEW bhapi.ai mobile app. Reuse the existing bhapi.com Figma designs as the design basis — adapt screen layouts, component patterns, and navigation flows for the social features. Apply bhapi.ai branding on top (Orange #FF6B35, Teal #0D9488, Inter font, BhapiLogo). Extend the Figma designs to include AI safety features (parent dashboard, alerts, screen time, location) which don't exist in the original Figma.

**Files:**
- `mobile/src/app/` — Expo Router file-based routing
- `mobile/src/lib/api.ts` — API client (same patterns as portal)
- `mobile/src/lib/auth.ts` — SecureStore token management (from Task 3.3)
- `mobile/src/components/ui/` — Shared UI components (Button, Card, Input)
- `mobile/src/theme/` — Brand colors (#FF6B35, #0D9488), Inter font

- [ ] **Steps 1-6: Auth flow (login, register, VPC), navigation scaffold, theme**

---

### Task 6.2: Parent Dashboard (Mobile)

**Files:**
- `mobile/src/app/(parent)/dashboard.tsx`
- `mobile/src/app/(parent)/alerts.tsx`
- `mobile/src/app/(parent)/consent.tsx`
- `mobile/src/hooks/use-dashboard.ts`

- [ ] **Steps 1-6: Port key dashboard views from web portal to mobile**

---

### Task 6.3: Child Social Experience (Mobile)

**Files:**
- `mobile/src/app/(child)/feed.tsx`
- `mobile/src/app/(child)/messages.tsx`
- `mobile/src/app/(child)/profile.tsx`

- [ ] **Steps 1-6: Social feed, messaging, profile for child users**

---

### Task 6.4: Device Agent — AI App Monitoring

**Files:**
- `mobile/src/services/device-agent.ts` — Background monitoring service
- `mobile/src/services/ai-app-detector.ts` — Detect AI app usage

**iOS:** MDM profile or Screen Time API integration
**Android:** Accessibility Service or UsageStats API

- [ ] **Step 1: Research platform-specific monitoring capabilities**

iOS constraints:
- Screen Time API (iOS 15+) for app usage data
- MDM profile for managed devices (school deployment)
- No content capture from other apps (sandbox)

Android constraints:
- UsageStatsManager for app usage time
- Accessibility Service for content capture (requires user approval)
- Device Admin for managed devices

- [ ] **Step 2: Implement app usage tracking (both platforms)**
- [ ] **Step 3: Implement notification monitoring (AI app push notifications)**
- [ ] **Step 4: Real-time sync to backend**
- [ ] **Step 5: Test on physical devices**
- [ ] **Step 6: Commit**

---

### Task 6.5: Screen Time Management

**Files:**
- Create: `src/screen_time/` — Backend module
  - `router.py`, `service.py`, `models.py`, `schemas.py`
- Create: `mobile/src/app/(parent)/screen-time.tsx`
- Create: `tests/e2e/test_screen_time_e2e.py`

Features:
- Per-app time limits (extending existing time budgets)
- Screen time scheduling (school hours, homework, free time)
- "One more minute" extension requests (parent approval via push)
- Daily/weekly/monthly screen time reports

- [ ] **Steps 1-8: Full TDD cycle**

---

### Task 6.6: Location Tracking

**Files:**
- Create: `src/location/` — Backend module
  - `router.py`, `service.py`, `models.py`, `schemas.py`
- Create: `mobile/src/services/location.ts`
- Create: `mobile/src/app/(parent)/location.tsx`
- Create: `tests/e2e/test_location_e2e.py`

Features:
- Real-time child location (with consent)
- Geofencing (school, home, allowed zones) with alerts
- Location history timeline
- Panic button integration (existing F10) with location attachment

- [ ] **Steps 1-8: Full TDD cycle**

---

## Sub-Plan 7: Unified Dashboard, Competitive Features & Bundle

**Effort: 14-20 person-weeks**
**Dependencies: Sub-Plans 5 and 6**

### Context

The bhapi.ai web portal becomes the **single unified dashboard** for everything: AI safety monitoring, social activity oversight, content moderation, family management, school admin, and back-office operations. Parents log into bhapi.ai and see BOTH their child's AI usage AND their child's social activity in one place. The back-office admin pages (from Sub-Plan 5 Task 5.7) are already built by this phase.

### Task 7.1: AI Mood/Wellbeing Analysis

**Files:**
- Create: `src/wellbeing/` — Backend module
  - `router.py`, `service.py`, `models.py`, `schemas.py`
- Create: `tests/e2e/test_wellbeing_e2e.py`

Features:
- Longitudinal mood tracking across AI conversations
- Emotional pattern alerts (sustained negative sentiment)
- Wellbeing score with contributing factors
- Privacy-preserving sentiment analysis (aggregate signals, not content)

- [ ] **Steps 1-8: Full TDD cycle**

---

### Task 7.2: Unified Family Dashboard (Social + AI in One View)

**Files:**
- Modify: `src/portal/service.py` — Aggregate social + AI safety + screen time + location
- Create: `portal/src/app/(dashboard)/family/page.tsx` — Replaces separate dashboards
- Create: `tests/e2e/test_unified_dashboard_e2e.py`

This is the **primary parent view** at bhapi.ai — everything about their child in one place:

```
┌─────────────────────────────────────────────────────────────┐
│  BHAPI FAMILY DASHBOARD — [Child Name]                       │
├─────────────────────────┬───────────────────────────────────┤
│  AI SAFETY              │  SOCIAL ACTIVITY                  │
│  ● Risk score: 72/100   │  ● Posts today: 3                 │
│  ● AI chats today: 7    │  ● Messages: 12                   │
│  ● Flagged: 1 convo     │  ● New connections: 1             │
│  ● Platforms: ChatGPT,  │  ● Moderation flags: 0            │
│    Claude, Gemini       │  ● Time on social: 45m            │
├─────────────────────────┴───────────────────────────────────┤
│  SCREEN TIME                    │  LOCATION                  │
│  Total: 2h 15m (▼12% vs avg)   │  📍 School (since 8:30am)  │
│  ██████████░░░ AI: 45m          │  Geofence: ✅ In zone      │
│  ████████░░░░░ Social: 35m      │  Last check-in: 12:15pm   │
│  ████░░░░░░░░░ Other: 55m       │                            │
├─────────────────────────────────┴────────────────────────────┤
│  WELLBEING SCORE: 85/100                                      │
│  ● Mood trend: Stable  ● Social engagement: Healthy           │
│  ● AI dependency risk: Low  ● Action needed: Review 1 flag    │
└──────────────────────────────────────────────────────────────┘
```

- [ ] **Steps 1-6: Full TDD cycle**

---

### Task 7.3: Bundle Pricing & Subscription Tiers

**Files:**
- Modify: `src/billing/service.py` — Add new plan tiers
- Modify: `src/billing/models.py` — New plan definitions
- Create: `portal/src/app/(dashboard)/pricing/page.tsx` — Updated pricing page

| Tier | Includes | Price |
|---|---|---|
| Bhapi Safety | AI Portal only | $9.99/mo |
| Bhapi Social | Social features | Free (premium $4.99/mo) |
| **Bhapi Family** | AI + Social + Mobile Agent | **$14.99/mo** |
| Bhapi School | AI + Governance (per-seat) | $4-8/student/yr |
| Bhapi Enterprise | All + API + Support | Custom |

- [ ] **Steps 1-4: Update Stripe plans, billing logic, pricing page, test**

---

### Task 7.4: Public API with SDKs

**Files:**
- Create: `src/api_public/` — Public API module with OAuth 2.0
- Create: `portal/src/app/(dashboard)/developer/api-docs/page.tsx` — Interactive API docs
- Create: `tests/e2e/test_public_api_e2e.py`

- [ ] **Steps 1-6: OAuth 2.0 auth, rate limiting tiers, interactive docs**

---

### Task 7.5: Cross-Product Data Intelligence

**Files:**
- Create: `src/intelligence/` — Cross-product signal aggregation
  - Combine social behavior + AI usage for richer safety insights
  - Example: Social activity drops + AI chatbot usage spikes → dependency risk alert

- [ ] **Steps 1-6: Full TDD cycle**

---

## Explicitly Deferred Gaps

The following High/Medium-priority gaps from the gap analysis are **intentionally excluded** from this 6-month plan:

| Gap ID | Name | Priority | Effort | Why Deferred |
|---|---|---|---|---|
| P-H3 | Social Media Monitoring (30+ platforms) | High | 14-20 pw | Requires mobile device agent (P-C1, Sub-Plan 6) to be in production. Bark's 30+ platform coverage is achieved via device-level monitoring, not APIs. Too large for the 6-month window. Re-evaluate Q4 2026. |
| P-H5 | VR/Metaverse Monitoring | High | 8-12 pw | Market adoption still early. Only Qustodio has moved here. Not table-stakes yet. Re-evaluate Q4 2026. |
| P-M2 | Gaming Safety | Medium | 10-14 pw | Aura has 200+ games; partnership approach better than build. Evaluate in Q4 2026. |
| P-M3 | Community Safety Intelligence | Medium | 6-8 pw | Needs critical mass of users first. Premature before school/family growth in Phase 3. |
| P-M5 | Identity Theft Protection Partnership | Medium | 2-4 pw | Business development timeline. Evaluate in Q4 2026. |
| A-C2 | React Native 0.64 Upgrade | Critical (was) | 8-12 pw | **Superseded by ADR-004** — greenfield Expo SDK 52+ replaces the upgrade path entirely. |
| A-C3 | Legacy App Test Coverage | Critical (was) | 12-17 pw | **Superseded by ADR-004/005** — legacy repos are archived, not maintained. |
| A-M1 | Stories/Reels | Medium | 8-12 pw | App stabilization (now: greenfield) must complete first. Phase 4+ feature. |
| A-M2 | Safe AI Creative Tools | Medium | 8-10 pw | Nice-to-have after social foundation ships. |
| A-M3 | Educational Content Integration | Medium | 6-8 pw | Partnership-dependent; not a build task. |

**Effort reconciliation:** This plan covers approximately **70-96 person-weeks** of the gap analysis's 127-175 pw total. The delta is accounted for by the deferred gaps above and by the ADR-004/005 decisions that eliminate ~26-37 pw of legacy app stabilization work (A-C1 partially, A-C2, A-C3 fully) by replacing them with a greenfield mobile app (Sub-Plan 6).

## Phase 0 Priority Note

Sub-Plans 1, 2, and 3 are all in Phase 0 but have different urgency levels:
- **Sub-Plan 1 (COPPA): Hard deadline Apr 22 — non-negotiable**
- **Sub-Plan 2 (Legacy triage): Should start immediately — security risk**
- **Sub-Plan 3 (Unification foundation): Can begin in Phase 0 but is allowed to slip into Phase 1 start without consequences for COPPA**

If the team is 2-4 engineers, prioritize Sub-Plans 1 and 2 in parallel. Sub-Plan 3 starts after COPPA compliance is secured.

## MongoDB Migration

**Deferred.** The unified platform is built fresh with no connection to the current bhapi.com MongoDB. User migration from the legacy social app can happen later as a separate initiative. ADR-003's ETL approach remains valid if/when migration is needed, but it is not in scope for this plan.

---

## Quality Gates

### Per-Phase Exit Criteria

| Phase | Exit Criteria |
|---|---|
| Phase 0 | COPPA 2026 compliant (legal sign-off). Legacy repos archived. All existing tests pass. |
| Phase 1 | Chrome Web Store listing live. Ohio governance MVP deployed. 15+ AI platforms monitored. Social posts/comments/followers modules complete with tests. |
| Phase 2 | Mobile app in TestFlight/Play Store beta. EU AI Act compliant. Screen time + location live. Device agent capturing AI app usage. Messaging module complete. |
| Phase 3 | Unified dashboard live. Bundle pricing live. Public API in beta. 5+ school deployments. Wellbeing analysis in beta. |

### Continuous Quality Standards

- **Test coverage:** Every new module has unit + E2E + security tests
- **CI:** `pytest tests/ -v` + `cd portal && npx vitest run` + `cd portal && npx tsc --noEmit` all pass
- **Security:** No new Snyk/dependabot vulnerabilities unaddressed for >7 days
- **Performance:** API response time <200ms p95 for read endpoints
- **Accessibility:** WCAG 2.1 AA for all new pages
- **i18n:** All user-facing strings in 6 languages
- **Documentation:** CLAUDE.md updated after each module addition

---

## Resource Requirements

### Engineering Headcount (Recommended)

| Role | Count | Focus |
|---|---|---|
| Senior Backend (Python/FastAPI) | 2 | COPPA, social modules, compliance, APIs |
| Mobile (Expo/React Native) | 2 | Mobile app, device agent |
| Frontend (React/Next.js) | 1 | Portal pages, unified dashboard |
| ML/AI Engineer | 1 | Wellbeing analysis, threat detection |
| DevOps/Security | 1 (fractional) | CI/CD, security hardening, pen testing |

### Key External Costs

| Item | Cost | When |
|---|---|---|
| Legal counsel (COPPA + EU AI Act) | $15-30K | Immediate (Phase 0) |
| Apple Developer Enterprise | $299/yr | Phase 2 |
| Penetration testing | $10-20K | Phase 1 |
| SOC 2 Type II audit | $30-50K | Phase 3+ |

---

## Appendix: ADR Index

| ADR | Decision | Sub-Plan |
|---|---|---|
| ADR-001 | Unified auth (Portal's JWT + API keys) | Sub-Plan 3 |
| ADR-002 | Social modules in FastAPI backend | Sub-Plan 5 |
| ADR-003 | MongoDB → PostgreSQL migration | Sub-Plan 2 |
| ADR-004 | Mobile greenfield on Expo SDK 52+ | Sub-Plan 6 |
| ADR-005 | Single repo, archive legacy | Sub-Plan 2, 3 |

---

*This plan should be reviewed weekly. Next review: March 24, 2026.*
*Regulatory deadlines are non-negotiable. Feature deadlines are adjustable.*
