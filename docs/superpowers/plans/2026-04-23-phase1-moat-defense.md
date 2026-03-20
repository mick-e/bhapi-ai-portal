# Phase 1: Moat Defense + Safety Foundation — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the school market entry, Safety app MVP, content moderation pipeline, real-time WebSocket service, and social backend foundation — establishing Bhapi's competitive moat as "the only platform where kids socialize safely AND parents monitor AI."

**Architecture:** Extends the existing FastAPI monolith (`src/main.py`) with 7 new backend modules (`moderation/`, `social/`, `contacts/`, `age_tier/`, `governance/`, `media/`, `messaging/`) + a separate WebSocket real-time service (`src/realtime/`). Mobile Safety app built on the existing Expo monorepo scaffold (`mobile/`) with enhanced shared packages. Browser extension enhanced for school Chromebook deployment. All new tables via Alembic migrations 032-038.

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy async / Alembic / PostgreSQL 16 | Expo SDK 52+ / React Native / TypeScript / Turborepo | Manifest V3 browser extension | Redis 7 | Cloudflare R2/Images/Stream | Hive/Sensity (image/video moderation) | PhotoDNA (CSAM detection)

**Spec:** `docs/superpowers/specs/2026-03-19-bhapi-unified-platform-design.md` (v1.2, Section 8 Phase 1)

**Duration:** Weeks 6-12 (Apr 23 — Jun 8, 2026)
**Team:** 5-7 engineers
**Budget:** 35-49 person-weeks
**Phase 0 exit:** All 14 tasks complete, 1,887+ tests passing

---

## Dependency Graph

```
FOUNDATION LAYER (Tasks 1-3, do first)
  Task 1: Age Tier module ─────────────────┐
  Task 2: Social DB models + migrations ───┤
  Task 3: Moderation module ───────────────┘
       │                                    │
       ├──► BACKEND FEATURES (Tasks 4-14)   │
       │    Task 4: Text classifier ────────┤
       │    Task 5: Image moderation ───────┤
       │    Task 6: Video moderation ───────┤
       │    Task 7: Social risk models ─────┤
       │    Task 8: CSAM + NCMEC ───────────┤
       │    Task 9: Social module ──────────┤
       │    Task 10: Contacts module ───────┘
       │    Task 11: Australian safety
       │    Task 12: Governance module
       │    Task 13: Media module (CF R2/Images/Stream) — see Task 28
       │    Task 14: Messaging module (skeleton) — see Task 29
       │
       ├──► REAL-TIME (Tasks 13-14, independent)
       │    Task 13: WebSocket service + Redis pub/sub
       │    Task 14: Push relay + Presence
       │
       ├──► MOBILE (Tasks 15-20, independent of backend)
       │    Task 15: shared-auth + shared-api + shared-types
       │    Task 16: shared-i18n + shared-ui
       │    Task 17: Safety app auth screens
       │    Task 18: Safety app dashboard + alerts
       │    Task 19: Safety app groups + push
       │    Task 20: Social app screen shells + shared-ui social
       │
       ├──► SCHOOL MARKET (Tasks 21-25, independent)
       │    Task 21: Google Admin Console integration
       │    Task 22: School IT admin dashboard (depends on Task 21)
       │    Task 23: Chromebook extension
       │    Task 24: Compliance reporting
       │    Task 25: Chrome Web Store enterprise listing
       │
       └──► ADDITIONAL BACKEND (Tasks 28-29, after foundation)
            Task 28: Media module (CF R2/Images/Stream)
            Task 29: Messaging module (skeleton)

SCHOOL OPS (Task 30, after Tasks 21-25)
  Task 30: School pilot outreach + onboarding

DOCUMENTATION (Task 31, independent)
  Task 31: T&S ops + FERPA + school procurement

RELEASE (Task 32, depends on Tasks 17-20)
  Task 32: TestFlight + Android internal testing
```

**Parallelization:** Tasks within each group can run concurrently (except Task 24 depends on Task 23). Foundation layer must complete before backend features. Mobile and school tracks are fully independent of backend.

---

## File Structure

### New Backend Modules

```
src/
├── age_tier/                    # NEW — Permission engine
│   ├── __init__.py              # Public interface
│   ├── router.py                # /api/v1/age-tier endpoints
│   ├── service.py               # Tier assignment, permission checks
│   ├── models.py                # AgeTierConfig model
│   ├── schemas.py               # Pydantic schemas
│   └── rules.py                 # Feature permission matrix
│
├── moderation/                  # NEW — Content moderation pipeline
│   ├── __init__.py              # Public interface
│   ├── router.py                # /api/v1/moderation endpoints
│   ├── service.py               # Pipeline orchestration
│   ├── models.py                # ModerationQueue, ModerationDecision, ContentReport, MediaAsset
│   ├── schemas.py               # Pydantic schemas
│   ├── keyword_filter.py        # Fast-path <100ms keyword matching
│   ├── image_pipeline.py        # CF Images webhook → Hive/Sensity
│   ├── video_pipeline.py        # CF Stream → frame extract → classify
│   ├── csam.py                  # PhotoDNA + NCMEC CyberTipline
│   └── social_risk.py           # Grooming, cyberbullying, sexting models
│
├── social/                      # NEW — Feed, posts, profiles
│   ├── __init__.py              # Public interface
│   ├── router.py                # /api/v1/social endpoints
│   ├── service.py               # Feed CRUD, profile CRUD, follow/unfollow
│   ├── models.py                # Profile, SocialPost, PostComment, PostLike, Hashtag, Follow
│   └── schemas.py               # Pydantic schemas
│
├── contacts/                    # NEW — Contact requests with parent gate
│   ├── __init__.py              # Public interface
│   ├── router.py                # /api/v1/contacts endpoints
│   ├── service.py               # Request, approve, block
│   ├── models.py                # Contact, ContactApproval
│   └── schemas.py               # Pydantic schemas
│
├── governance/                  # NEW — School AI policy management
│   ├── __init__.py              # Public interface
│   ├── router.py                # /api/v1/governance endpoints
│   ├── service.py               # Policy CRUD, template generation, audit
│   ├── models.py                # GovernancePolicy, GovernanceAudit
│   └── schemas.py               # Pydantic schemas
│
├── media/                       # NEW — Cloudflare media management
│   ├── __init__.py              # Public interface
│   ├── router.py                # /api/v1/media endpoints
│   ├── service.py               # Upload, resize, transcode orchestration
│   ├── models.py                # MediaAsset (moved from moderation)
│   └── schemas.py               # Pydantic schemas
│
├── messaging/                   # NEW — Chat messaging (skeleton in P1, full in P2)
│   ├── __init__.py              # Public interface
│   ├── router.py                # /api/v1/messages endpoints
│   ├── service.py               # Conversation CRUD, message send
│   ├── models.py                # Conversation, ConversationMember, Message, MessageMedia
│   └── schemas.py               # Pydantic schemas
│
└── realtime/                    # NEW — Separate WebSocket service
    ├── main.py                  # WebSocket FastAPI app
    ├── auth.py                  # JWT validation (shared secret)
    ├── connections.py           # Connection management, heartbeat
    ├── presence.py              # Online/offline/last-seen via Redis
    ├── notifications.py         # Push notification relay
    └── pubsub.py                # Redis pub/sub bridge
```

### New Alembic Migrations

```
alembic/versions/
├── 032_social_profiles_age_tiers.py    # profiles, age_tier_configs tables
├── 033_social_posts.py                  # social_posts, post_comments, post_likes, hashtags, post_hashtags
├── 034_follows_contacts.py              # follows, contacts, contact_approvals
├── 035_moderation.py                    # moderation_queue, moderation_decisions, content_reports, media_assets
├── 036_governance.py                    # governance_policies, governance_audits
├── 037_messaging.py                     # conversations, conversation_members, messages, message_media
└── 038_indexes.py                       # Compound indexes for social queries
```

### New Test Files

```
tests/
├── unit/
│   ├── test_age_tier.py
│   ├── test_moderation.py
│   ├── test_moderation_keyword.py
│   ├── test_moderation_image.py
│   ├── test_moderation_video.py
│   ├── test_moderation_csam.py
│   ├── test_moderation_social_risk.py
│   ├── test_social.py
│   ├── test_contacts.py
│   ├── test_governance.py
│   ├── test_media.py
│   ├── test_messaging.py
│   ├── test_realtime.py
│   └── test_realtime_presence.py
├── e2e/
│   ├── test_age_tier.py
│   ├── test_moderation.py
│   ├── test_moderation_keyword.py
│   ├── test_moderation_image.py
│   ├── test_moderation_video.py
│   ├── test_moderation_social_risk.py
│   ├── test_social.py
│   ├── test_contacts.py
│   ├── test_governance.py
│   ├── test_media.py
│   └── test_messaging.py
└── security/
    ├── test_age_tier_security.py
    ├── test_moderation_security.py
    ├── test_moderation_image_security.py
    ├── test_moderation_video_security.py
    ├── test_social_security.py
    ├── test_contacts_security.py
    ├── test_governance_security.py
    └── test_media_security.py
```

### Mobile Changes

```
mobile/
├── packages/
│   ├── shared-auth/src/
│   │   ├── token-manager.ts     # MODIFY — add SecureStore, biometrics, refresh
│   │   ├── secure-store.ts      # NEW
│   │   ├── biometric.ts         # NEW
│   │   └── session.ts           # NEW
│   ├── shared-api/src/
│   │   ├── rest-client.ts       # MODIFY — add interceptors, retry, offline queue
│   │   ├── ws-client.ts         # NEW — WebSocket client
│   │   └── offline-queue.ts     # NEW
│   ├── shared-i18n/
│   │   └── locales/*.json       # MODIFY — add safety/social app strings
│   ├── shared-ui/src/
│   │   ├── BhapiLogo.tsx        # NEW
│   │   ├── Button.tsx           # NEW (replace stub)
│   │   ├── Card.tsx             # NEW
│   │   ├── Input.tsx            # NEW
│   │   ├── Badge.tsx            # NEW
│   │   ├── Toast.tsx            # NEW
│   │   ├── Avatar.tsx           # NEW
│   │   ├── PostCard.tsx         # NEW (Track E)
│   │   ├── CommentThread.tsx    # NEW (Track E)
│   │   ├── MessageBubble.tsx    # NEW (Track E)
│   │   └── ContactRequest.tsx   # NEW (Track E)
│   └── shared-types/src/
│       ├── social.ts            # NEW
│       ├── safety.ts            # NEW
│       └── moderation.ts        # NEW
├── apps/
│   ├── safety/app/
│   │   ├── _layout.tsx          # REPLACE placeholder
│   │   ├── (auth)/
│   │   │   ├── login.tsx
│   │   │   ├── register.tsx
│   │   │   └── magic-link.tsx
│   │   ├── (dashboard)/
│   │   │   ├── index.tsx
│   │   │   ├── alerts.tsx
│   │   │   └── alert-detail.tsx
│   │   ├── (children)/
│   │   │   └── index.tsx
│   │   └── (settings)/
│   │       └── index.tsx
│   └── social/app/
│       ├── _layout.tsx          # REPLACE placeholder
│       ├── (auth)/login.tsx
│       ├── (feed)/index.tsx
│       ├── (chat)/index.tsx
│       ├── (profile)/index.tsx
│       └── (settings)/index.tsx
```

### Extension Changes

```
extension/
├── src/
│   ├── google-admin.ts          # NEW — MDM deployment support
│   ├── offline-cache.ts         # NEW — Chromebook offline
│   └── school-policy.ts         # NEW — School policy enforcement
```

---

## Task 1: Age Tier Module (P1-H4)

**Deliverable:** `src/age_tier/` — Permission engine with tier assignment, rule matrix, and graduated feature unlocks.

**Files:**
- Create: `src/age_tier/__init__.py`
- Create: `src/age_tier/models.py`
- Create: `src/age_tier/schemas.py`
- Create: `src/age_tier/rules.py`
- Create: `src/age_tier/service.py`
- Create: `src/age_tier/router.py`
- Modify: `src/main.py` (register router)
- Modify: `alembic/env.py` (import model)
- Test: `tests/unit/test_age_tier.py`
- Test: `tests/e2e/test_age_tier.py`
- Test: `tests/security/test_age_tier_security.py`

- [ ] **Step 1: Write unit tests for the rules engine**

```python
# tests/unit/test_age_tier.py
"""Unit tests for the age tier permission engine."""

import pytest
from datetime import date, timedelta


class TestAgeTierRules:
    """Test the feature permission matrix."""

    def test_young_tier_5_to_9(self):
        from src.age_tier.rules import get_tier_for_age, AgeTier
        assert get_tier_for_age(5) == AgeTier.YOUNG
        assert get_tier_for_age(9) == AgeTier.YOUNG

    def test_preteen_tier_10_to_12(self):
        from src.age_tier.rules import get_tier_for_age, AgeTier
        assert get_tier_for_age(10) == AgeTier.PRETEEN
        assert get_tier_for_age(12) == AgeTier.PRETEEN

    def test_teen_tier_13_to_15(self):
        from src.age_tier.rules import get_tier_for_age, AgeTier
        assert get_tier_for_age(13) == AgeTier.TEEN
        assert get_tier_for_age(15) == AgeTier.TEEN

    def test_out_of_range_raises(self):
        from src.age_tier.rules import get_tier_for_age
        with pytest.raises(ValueError, match="outside supported"):
            get_tier_for_age(4)
        with pytest.raises(ValueError, match="outside supported"):
            get_tier_for_age(16)

    def test_age_from_dob(self):
        from src.age_tier.rules import age_from_dob
        today = date.today()
        dob_10 = today.replace(year=today.year - 10)
        assert age_from_dob(dob_10) == 10

    def test_young_tier_permissions(self):
        from src.age_tier.rules import get_permissions, AgeTier
        perms = get_permissions(AgeTier.YOUNG)
        assert perms["can_post"] is True
        assert perms["can_message"] is False  # Young can't DM
        assert perms["can_follow"] is True
        assert perms["moderation_mode"] == "pre_publish"
        assert perms["can_upload_video"] is False
        assert perms["max_contacts"] == 10

    def test_preteen_tier_permissions(self):
        from src.age_tier.rules import get_permissions, AgeTier
        perms = get_permissions(AgeTier.PRETEEN)
        assert perms["can_post"] is True
        assert perms["can_message"] is True
        assert perms["moderation_mode"] == "pre_publish"  # Images only
        assert perms["can_upload_video"] is False
        assert perms["max_contacts"] == 25

    def test_teen_tier_permissions(self):
        from src.age_tier.rules import get_permissions, AgeTier
        perms = get_permissions(AgeTier.TEEN)
        assert perms["can_post"] is True
        assert perms["can_message"] is True
        assert perms["moderation_mode"] == "post_publish"
        assert perms["can_upload_video"] is True
        assert perms["max_contacts"] == 100

    def test_check_permission_allowed(self):
        from src.age_tier.rules import check_permission, AgeTier
        assert check_permission(AgeTier.TEEN, "can_post") is True

    def test_check_permission_denied(self):
        from src.age_tier.rules import check_permission, AgeTier
        assert check_permission(AgeTier.YOUNG, "can_message") is False

    def test_check_permission_unknown_raises(self):
        from src.age_tier.rules import check_permission, AgeTier
        with pytest.raises(KeyError):
            check_permission(AgeTier.YOUNG, "nonexistent_perm")

    def test_feature_override_applied(self):
        from src.age_tier.rules import get_permissions, AgeTier
        overrides = {"can_message": True}
        perms = get_permissions(AgeTier.YOUNG, feature_overrides=overrides)
        assert perms["can_message"] is True

    def test_locked_feature_not_overridable(self):
        from src.age_tier.rules import get_permissions, AgeTier
        overrides = {"can_message": True}
        locked = ["can_message"]
        perms = get_permissions(AgeTier.YOUNG, feature_overrides=overrides, locked_features=locked)
        assert perms["can_message"] is False  # Locked wins

    def test_all_tiers_have_same_permission_keys(self):
        from src.age_tier.rules import get_permissions, AgeTier
        keys_young = set(get_permissions(AgeTier.YOUNG).keys())
        keys_preteen = set(get_permissions(AgeTier.PRETEEN).keys())
        keys_teen = set(get_permissions(AgeTier.TEEN).keys())
        assert keys_young == keys_preteen == keys_teen

    def test_young_cannot_upload_video(self):
        from src.age_tier.rules import get_permissions, AgeTier
        perms = get_permissions(AgeTier.YOUNG)
        assert perms["can_upload_video"] is False
        assert perms["can_share_location"] is False

    def test_teen_max_post_length(self):
        from src.age_tier.rules import get_permissions, AgeTier
        assert get_permissions(AgeTier.TEEN)["max_post_length"] == 1000
        assert get_permissions(AgeTier.YOUNG)["max_post_length"] == 200

    def test_preteen_search_allowed(self):
        from src.age_tier.rules import get_permissions, AgeTier
        assert get_permissions(AgeTier.PRETEEN)["can_search_users"] is True
        assert get_permissions(AgeTier.YOUNG)["can_search_users"] is False

    def test_daily_post_limits_per_tier(self):
        from src.age_tier.rules import get_permissions, AgeTier
        assert get_permissions(AgeTier.YOUNG)["max_daily_posts"] == 10
        assert get_permissions(AgeTier.PRETEEN)["max_daily_posts"] == 25
        assert get_permissions(AgeTier.TEEN)["max_daily_posts"] == 50

    def test_multiple_overrides_applied(self):
        from src.age_tier.rules import get_permissions, AgeTier
        overrides = {"can_message": True, "max_contacts": 15}
        perms = get_permissions(AgeTier.YOUNG, feature_overrides=overrides)
        assert perms["can_message"] is True
        assert perms["max_contacts"] == 15

    def test_empty_overrides_no_change(self):
        from src.age_tier.rules import get_permissions, AgeTier
        perms_default = get_permissions(AgeTier.YOUNG)
        perms_empty = get_permissions(AgeTier.YOUNG, feature_overrides={})
        assert perms_default == perms_empty

    def test_age_boundary_9_10(self):
        from src.age_tier.rules import get_tier_for_age, AgeTier
        assert get_tier_for_age(9) == AgeTier.YOUNG
        assert get_tier_for_age(10) == AgeTier.PRETEEN

    def test_age_boundary_12_13(self):
        from src.age_tier.rules import get_tier_for_age, AgeTier
        assert get_tier_for_age(12) == AgeTier.PRETEEN
        assert get_tier_for_age(13) == AgeTier.TEEN

    def test_dob_birthday_edge_case(self):
        from src.age_tier.rules import age_from_dob
        from datetime import date
        today = date.today()
        # Birthday is tomorrow — still previous age
        dob = date(today.year - 10, today.month, today.day + 1) if today.day < 28 else date(today.year - 10, today.month, today.day)
        age = age_from_dob(dob)
        assert age in (9, 10)  # Either 9 (birthday tomorrow) or 10 (birthday today)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_age_tier.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.age_tier'`

- [ ] **Step 3: Implement the rules engine**

Create `src/age_tier/__init__.py`:
```python
"""Age tier permission engine module.

Public interface for cross-module communication.
Other modules should import only from this file.
"""

from src.age_tier.rules import AgeTier, get_tier_for_age, get_permissions, check_permission, age_from_dob

__all__ = [
    "AgeTier",
    "get_tier_for_age",
    "get_permissions",
    "check_permission",
    "age_from_dob",
]
```

Create `src/age_tier/rules.py`:
```python
"""Age tier permission matrix.

Three tiers per ADR-009:
  - YOUNG (5-9): Maximum restrictions, pre-publish moderation on everything
  - PRETEEN (10-12): Moderate restrictions, pre-publish on images/video
  - TEEN (13-15): Minimal restrictions, post-publish moderation
"""

from datetime import date
from enum import StrEnum


class AgeTier(StrEnum):
    YOUNG = "young"      # 5-9
    PRETEEN = "preteen"  # 10-12
    TEEN = "teen"        # 13-15


# Canonical permission matrix — source of truth for all tier-based decisions
_PERMISSION_MATRIX: dict[AgeTier, dict[str, bool | str | int]] = {
    AgeTier.YOUNG: {
        "can_post": True,
        "can_comment": True,
        "can_like": True,
        "can_follow": True,
        "can_message": False,
        "can_upload_image": True,
        "can_upload_video": False,
        "can_share_location": False,
        "can_create_group_chat": False,
        "can_search_users": False,
        "moderation_mode": "pre_publish",
        "max_contacts": 10,
        "max_post_length": 200,
        "max_daily_posts": 10,
    },
    AgeTier.PRETEEN: {
        "can_post": True,
        "can_comment": True,
        "can_like": True,
        "can_follow": True,
        "can_message": True,
        "can_upload_image": True,
        "can_upload_video": False,
        "can_share_location": False,
        "can_create_group_chat": False,
        "can_search_users": True,
        "moderation_mode": "pre_publish",  # Images/video only; text is post-publish
        "max_contacts": 25,
        "max_post_length": 500,
        "max_daily_posts": 25,
    },
    AgeTier.TEEN: {
        "can_post": True,
        "can_comment": True,
        "can_like": True,
        "can_follow": True,
        "can_message": True,
        "can_upload_image": True,
        "can_upload_video": True,
        "can_share_location": True,
        "can_create_group_chat": True,
        "can_search_users": True,
        "moderation_mode": "post_publish",
        "max_contacts": 100,
        "max_post_length": 1000,
        "max_daily_posts": 50,
    },
}

_AGE_RANGES = {
    AgeTier.YOUNG: (5, 9),
    AgeTier.PRETEEN: (10, 12),
    AgeTier.TEEN: (13, 15),
}


def age_from_dob(dob: date) -> int:
    """Calculate age in years from date of birth."""
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def get_tier_for_age(age: int) -> AgeTier:
    """Map an age to the corresponding tier."""
    for tier, (min_age, max_age) in _AGE_RANGES.items():
        if min_age <= age <= max_age:
            return tier
    raise ValueError(f"Age {age} is outside supported range (5-15)")


def get_permissions(
    tier: AgeTier,
    feature_overrides: dict[str, bool | str | int] | None = None,
    locked_features: list[str] | None = None,
) -> dict[str, bool | str | int]:
    """Get the full permission set for a tier, with optional overrides.

    Args:
        tier: The age tier.
        feature_overrides: Admin-configured overrides (e.g., school unlocks messaging for 10-12).
        locked_features: Features that cannot be overridden (safety lockdowns).
    """
    perms = dict(_PERMISSION_MATRIX[tier])
    locked = set(locked_features or [])

    if feature_overrides:
        for key, value in feature_overrides.items():
            if key in perms and key not in locked:
                perms[key] = value

    return perms


def check_permission(tier: AgeTier, permission: str) -> bool:
    """Check if a specific permission is allowed for a tier.

    Returns True/False for boolean permissions.
    Raises KeyError if the permission doesn't exist.
    """
    perms = _PERMISSION_MATRIX[tier]
    value = perms[permission]  # Raises KeyError if not found
    return bool(value)
```

- [ ] **Step 4: Run unit tests to verify they pass**

Run: `pytest tests/unit/test_age_tier.py -v`
Expected: All 15 tests PASS

- [ ] **Step 5: Create the model and schemas**

Create `src/age_tier/models.py`:
```python
"""Age tier configuration database model."""

import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin
from src.age_tier.rules import AgeTier


class AgeTierConfig(Base, UUIDMixin, TimestampMixin):
    """Per-member age tier configuration with jurisdiction overrides."""

    __tablename__ = "age_tier_configs"

    member_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("group_members.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    tier: Mapped[str] = mapped_column(
        Enum(AgeTier, name="age_tier_enum", create_constraint=True),
        nullable=False,
    )
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(2), nullable=False, default="US")
    feature_overrides: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    locked_features: Mapped[list | None] = mapped_column(JSONType, nullable=True)
```

Create `src/age_tier/schemas.py`:
```python
"""Age tier Pydantic schemas."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from src.age_tier.rules import AgeTier


class AgeTierConfigCreate(BaseModel):
    member_id: UUID
    date_of_birth: date
    jurisdiction: str = Field(default="US", max_length=2)
    feature_overrides: dict | None = None
    locked_features: list[str] | None = None


class AgeTierConfigResponse(BaseModel):
    id: UUID
    member_id: UUID
    tier: AgeTier
    date_of_birth: date
    jurisdiction: str
    feature_overrides: dict | None
    locked_features: list[str] | None
    permissions: dict

    model_config = {"from_attributes": True}


class PermissionCheckResponse(BaseModel):
    allowed: bool
    tier: AgeTier
    permission: str
```

- [ ] **Step 6: Create the service layer**

Create `src/age_tier/service.py`:
```python
"""Age tier service — tier assignment and permission enforcement."""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.age_tier.models import AgeTierConfig
from src.age_tier.rules import AgeTier, age_from_dob, get_permissions, get_tier_for_age
from src.exceptions import NotFoundError, ValidationError

logger = structlog.get_logger()


async def assign_tier(
    db: AsyncSession,
    member_id,
    date_of_birth,
    jurisdiction: str = "US",
    feature_overrides: dict | None = None,
    locked_features: list | None = None,
) -> AgeTierConfig:
    """Assign an age tier to a member based on their date of birth."""
    age = age_from_dob(date_of_birth)
    tier = get_tier_for_age(age)

    # Check for existing config
    result = await db.execute(
        select(AgeTierConfig).where(AgeTierConfig.member_id == member_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.tier = tier.value
        existing.date_of_birth = date_of_birth
        existing.jurisdiction = jurisdiction
        if feature_overrides is not None:
            existing.feature_overrides = feature_overrides
        if locked_features is not None:
            existing.locked_features = locked_features
        await db.flush()
        logger.info("age_tier_updated", member_id=str(member_id), tier=tier.value, age=age)
        return existing

    config = AgeTierConfig(
        member_id=member_id,
        tier=tier.value,
        date_of_birth=date_of_birth,
        jurisdiction=jurisdiction,
        feature_overrides=feature_overrides,
        locked_features=locked_features,
    )
    db.add(config)
    await db.flush()
    logger.info("age_tier_assigned", member_id=str(member_id), tier=tier.value, age=age)
    return config


async def get_member_permissions(db: AsyncSession, member_id) -> dict:
    """Get the full permission set for a member."""
    result = await db.execute(
        select(AgeTierConfig).where(AgeTierConfig.member_id == member_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise NotFoundError(f"No age tier config for member {member_id}")

    return get_permissions(
        AgeTier(config.tier),
        feature_overrides=config.feature_overrides,
        locked_features=config.locked_features,
    )


async def get_member_tier(db: AsyncSession, member_id) -> AgeTierConfig:
    """Get the tier config for a member."""
    result = await db.execute(
        select(AgeTierConfig).where(AgeTierConfig.member_id == member_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise NotFoundError(f"No age tier config for member {member_id}")
    return config
```

- [ ] **Step 7: Create the router**

Create `src/age_tier/router.py`:
```python
"""Age tier API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.age_tier import schemas
from src.age_tier.rules import AgeTier, get_permissions
from src.age_tier.service import assign_tier, get_member_permissions, get_member_tier
from src.dependencies import AuthContext, DbSession, require_permission

router = APIRouter()


@router.post("/assign", response_model=schemas.AgeTierConfigResponse)
async def assign_age_tier(
    payload: schemas.AgeTierConfigCreate,
    auth: AuthContext = Depends(),
    db: AsyncSession = Depends(DbSession),
):
    """Assign or update a member's age tier."""
    await require_permission(auth, "groups:manage")
    config = await assign_tier(
        db,
        member_id=payload.member_id,
        date_of_birth=payload.date_of_birth,
        jurisdiction=payload.jurisdiction,
        feature_overrides=payload.feature_overrides,
        locked_features=payload.locked_features,
    )
    perms = get_permissions(
        AgeTier(config.tier),
        feature_overrides=config.feature_overrides,
        locked_features=config.locked_features,
    )
    await db.commit()
    return schemas.AgeTierConfigResponse(
        id=config.id,
        member_id=config.member_id,
        tier=AgeTier(config.tier),
        date_of_birth=config.date_of_birth,
        jurisdiction=config.jurisdiction,
        feature_overrides=config.feature_overrides,
        locked_features=config.locked_features,
        permissions=perms,
    )


@router.get("/member/{member_id}", response_model=schemas.AgeTierConfigResponse)
async def get_tier(
    member_id: UUID,
    auth: AuthContext = Depends(),
    db: AsyncSession = Depends(DbSession),
):
    """Get a member's age tier configuration and permissions."""
    config = await get_member_tier(db, member_id)
    perms = get_permissions(
        AgeTier(config.tier),
        feature_overrides=config.feature_overrides,
        locked_features=config.locked_features,
    )
    return schemas.AgeTierConfigResponse(
        id=config.id,
        member_id=config.member_id,
        tier=AgeTier(config.tier),
        date_of_birth=config.date_of_birth,
        jurisdiction=config.jurisdiction,
        feature_overrides=config.feature_overrides,
        locked_features=config.locked_features,
        permissions=perms,
    )


@router.get("/member/{member_id}/permissions", response_model=dict)
async def get_permissions_endpoint(
    member_id: UUID,
    auth: AuthContext = Depends(),
    db: AsyncSession = Depends(DbSession),
):
    """Get just the permission set for a member."""
    return await get_member_permissions(db, member_id)


@router.get("/member/{member_id}/check/{permission}", response_model=schemas.PermissionCheckResponse)
async def check_permission_endpoint(
    member_id: UUID,
    permission: str,
    auth: AuthContext = Depends(),
    db: AsyncSession = Depends(DbSession),
):
    """Check if a member has a specific permission."""
    perms = await get_member_permissions(db, member_id)
    return schemas.PermissionCheckResponse(
        allowed=bool(perms.get(permission, False)),
        tier=AgeTier((await get_member_tier(db, member_id)).tier),
        permission=permission,
    )
```

- [ ] **Step 8: Register router in main.py and add model import to alembic/env.py**

Add to `src/main.py` in `_register_routers()`:
```python
    from src.age_tier.router import router as age_tier_router
    app.include_router(age_tier_router, prefix="/api/v1/age-tier", tags=["Age Tier"])
```

Add to `alembic/env.py`:
```python
from src.age_tier.models import AgeTierConfig  # noqa: F401
```

- [ ] **Step 9: Write E2E tests**

Create `tests/e2e/test_age_tier.py` — 15+ tests covering:
- POST /assign with valid DOB for each tier
- GET /member/{id} returns correct tier + permissions
- GET /member/{id}/permissions returns permission dict
- GET /member/{id}/check/{perm} returns allowed/denied
- Invalid DOB (age outside 5-15) returns 422
- Feature overrides applied correctly
- Locked features cannot be overridden
- Re-assignment updates tier correctly
- Non-existent member returns 404

- [ ] **Step 10: Write security tests**

Create `tests/security/test_age_tier_security.py` — 10+ tests covering:
- All endpoints require authentication (401 without token)
- Assign requires groups:manage permission (403 for child role)
- Cross-group access denied (parent can't see other group's children)
- Child cannot modify own tier
- Rate limiting on assign endpoint

- [ ] **Step 11: Run all tests and verify pass counts**

Run: `pytest tests/unit/test_age_tier.py tests/e2e/test_age_tier.py tests/security/test_age_tier_security.py -v`
Expected: ≥40 tests PASS (unit ≥25, E2E ≥15, security ≥10)

- [ ] **Step 12: Commit**

```bash
git add src/age_tier/ tests/unit/test_age_tier.py tests/e2e/test_age_tier.py tests/security/test_age_tier_security.py
git commit -m "feat: add age_tier module — permission engine with 3-tier rule matrix (P1-H4)"
```

---

## Task 2: Social DB Models + Alembic Migrations (P1-H1)

**Deliverable:** Database models for profiles, posts, comments, likes, hashtags, follows, contacts, moderation, governance + Alembic migrations 032-037.

**Files:**
- Create: `src/social/models.py`
- Create: `src/contacts/models.py`
- Create: `src/moderation/models.py`
- Create: `src/governance/models.py`
- Create: `alembic/versions/032_social_profiles_age_tiers.py`
- Create: `alembic/versions/033_social_posts.py`
- Create: `alembic/versions/034_follows_contacts.py`
- Create: `alembic/versions/035_moderation.py`
- Create: `alembic/versions/036_governance.py`
- Create: `alembic/versions/037_indexes.py`
- Modify: `alembic/env.py` (import all new models)
- Test: `tests/unit/test_social_models.py`

- [ ] **Step 1: Write tests for model relationships and constraints**

```python
# tests/unit/test_social_models.py
"""Unit tests for social database models."""

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import date

from tests.conftest import make_test_group


@pytest.mark.asyncio
class TestProfileModel:
    async def test_create_profile(self, test_session):
        from src.social.models import Profile
        group, owner_id = await make_test_group(test_session)
        profile = Profile(
            user_id=owner_id,
            display_name="Test Kid",
            bio="I like coding",
            age_tier="preteen",
            date_of_birth=date(2014, 6, 15),
            visibility="friends_only",
        )
        test_session.add(profile)
        await test_session.flush()
        assert profile.id is not None
        assert profile.display_name == "Test Kid"

    async def test_profile_user_id_unique(self, test_session):
        from src.social.models import Profile
        from sqlalchemy.exc import IntegrityError
        group, owner_id = await make_test_group(test_session)
        p1 = Profile(user_id=owner_id, display_name="A", age_tier="teen", date_of_birth=date(2012, 1, 1))
        test_session.add(p1)
        await test_session.flush()
        p2 = Profile(user_id=owner_id, display_name="B", age_tier="teen", date_of_birth=date(2012, 1, 1))
        test_session.add(p2)
        with pytest.raises(IntegrityError):
            await test_session.flush()


@pytest.mark.asyncio
class TestSocialPostModel:
    async def test_create_post(self, test_session):
        from src.social.models import Profile, SocialPost
        group, owner_id = await make_test_group(test_session)
        profile = Profile(user_id=owner_id, display_name="Kid", age_tier="teen", date_of_birth=date(2012, 1, 1))
        test_session.add(profile)
        await test_session.flush()
        post = SocialPost(
            author_id=owner_id,
            content="Hello world!",
            post_type="text",
            moderation_status="approved",
        )
        test_session.add(post)
        await test_session.flush()
        assert post.id is not None

    async def test_post_soft_delete(self, test_session):
        from src.social.models import Profile, SocialPost
        group, owner_id = await make_test_group(test_session)
        profile = Profile(user_id=owner_id, display_name="Kid", age_tier="teen", date_of_birth=date(2012, 1, 1))
        test_session.add(profile)
        await test_session.flush()
        post = SocialPost(author_id=owner_id, content="test", post_type="text", moderation_status="approved")
        test_session.add(post)
        await test_session.flush()
        post.soft_delete()
        assert post.is_deleted is True


@pytest.mark.asyncio
class TestFollowModel:
    async def test_create_follow(self, test_session):
        from src.social.models import Follow, Profile
        group, uid1 = await make_test_group(test_session, name="G1")
        profile1 = Profile(user_id=uid1, display_name="A", age_tier="teen", date_of_birth=date(2012, 1, 1))
        test_session.add(profile1)
        from src.auth.models import User
        uid2 = uuid4()
        u2 = User(id=uid2, email=f"u2-{uuid4().hex[:8]}@example.com", display_name="B", account_type="family", email_verified=False, mfa_enabled=False)
        test_session.add(u2)
        await test_session.flush()
        profile2 = Profile(user_id=uid2, display_name="B", age_tier="teen", date_of_birth=date(2012, 1, 1))
        test_session.add(profile2)
        await test_session.flush()
        follow = Follow(follower_id=uid1, following_id=uid2, status="accepted")
        test_session.add(follow)
        await test_session.flush()
        assert follow.id is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_social_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.social'`

- [ ] **Step 3: Create all model files**

Create `src/social/__init__.py`, `src/contacts/__init__.py`, `src/moderation/__init__.py`, `src/governance/__init__.py` with empty public interfaces.

Create `src/social/models.py` with: `Profile`, `SocialPost`, `PostComment`, `PostLike`, `Hashtag`, `PostHashtag`, `Follow`
- All models use `UUIDMixin`, `TimestampMixin`; SocialPost/PostComment also use `SoftDeleteMixin`
- `Profile.user_id` → FK to `users.id`, unique
- `SocialPost.author_id` → FK to `users.id`
- `SocialPost.moderation_status` → enum: pending/approved/rejected/removed
- `Follow.status` → enum: pending/accepted/blocked
- Unique constraint on `(follower_id, following_id)`
- Unique constraint on `(post_id, user_id)` on PostLike

Create `src/contacts/models.py` with: `Contact`, `ContactApproval`
- `Contact.status` → enum: pending/accepted/rejected/blocked
- `Contact.parent_approval_status` → enum: pending/approved/denied/not_required

Create `src/moderation/models.py` with: `ModerationQueue`, `ModerationDecision`, `ContentReport`, `MediaAsset`
- `ModerationQueue.pipeline` → enum: pre_publish/post_publish
- `ModerationQueue.status` → enum: pending/approved/rejected/escalated
- `ModerationQueue.risk_scores` → JSONType
- `MediaAsset.moderation_status` → enum: pending/approved/rejected

Create `src/governance/models.py` with: `GovernancePolicy`, `GovernanceAudit`
- `GovernancePolicy.policy_type` → enum: ai_usage/tool_inventory/risk_assessment/governance
- `GovernancePolicy.content` → JSONType
- `GovernancePolicy.status` → enum: draft/active/archived

- [ ] **Step 4: Create Alembic migrations**

Run: `alembic revision --autogenerate -m "social profiles and age tiers"` for 032
Then repeat for 033-037, or manually create targeted migrations for each table group.

**Critical:** Import ALL new models in `alembic/env.py`:
```python
from src.social.models import Profile, SocialPost, PostComment, PostLike, Hashtag, PostHashtag, Follow  # noqa: F401
from src.contacts.models import Contact, ContactApproval  # noqa: F401
from src.moderation.models import ModerationQueue, ModerationDecision, ContentReport, MediaAsset  # noqa: F401
from src.governance.models import GovernancePolicy, GovernanceAudit  # noqa: F401
```

- [ ] **Step 5: Run model tests to verify they pass**

Run: `pytest tests/unit/test_social_models.py -v`
Expected: All 5+ tests PASS

- [ ] **Step 6: Write migration tests**

```python
# tests/unit/test_migrations.py (append)
"""Verify migrations 032-037 create expected tables."""

import pytest
from sqlalchemy import inspect

@pytest.mark.asyncio
async def test_social_tables_exist(test_engine):
    async with test_engine.connect() as conn:
        def check_tables(sync_conn):
            inspector = inspect(sync_conn)
            tables = inspector.get_table_names()
            for table in ["profiles", "social_posts", "post_comments", "post_likes",
                         "hashtags", "post_hashtags", "follows", "contacts",
                         "contact_approvals", "moderation_queue", "moderation_decisions",
                         "content_reports", "media_assets", "governance_policies",
                         "governance_audits", "age_tier_configs"]:
                assert table in tables, f"Missing table: {table}"
        await conn.run_sync(check_tables)
```

- [ ] **Step 7: Run all model and migration tests**

Run: `pytest tests/unit/test_social_models.py tests/unit/test_migrations.py -v`
Expected: ≥30 tests PASS (unit ≥20, migration ≥10)

- [ ] **Step 8: Commit**

```bash
git add src/social/ src/contacts/ src/moderation/ src/governance/ alembic/ tests/unit/test_social_models.py tests/unit/test_migrations.py
git commit -m "feat: add social DB models + Alembic migrations 032-037 (P1-H1)"
```

---

## Task 3: Moderation Module — Pipeline & Queue (P1-A6)

**Deliverable:** `src/moderation/` — Pipeline orchestration, moderation queue CRUD, takedown, dashboard API.

**Files:**
- Create: `src/moderation/service.py`
- Create: `src/moderation/router.py`
- Create: `src/moderation/schemas.py`
- Modify: `src/moderation/__init__.py` (public interface)
- Modify: `src/main.py` (register router)
- Test: `tests/unit/test_moderation.py`
- Test: `tests/e2e/test_moderation.py`
- Test: `tests/security/test_moderation_security.py`

- [ ] **Step 1: Write unit tests for moderation service**

Test: queue CRUD (create queue entry, list queue, get by ID, update status), takedown flow (mark content removed, create decision record), pipeline routing (pre-publish vs post-publish based on age tier), dashboard stats (pending count, average processing time, severity breakdown).

≥35 unit tests.

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement moderation schemas**

Create `src/moderation/schemas.py` with: `ModerationQueueCreate`, `ModerationQueueResponse`, `ModerationDecisionCreate`, `ContentReportCreate`, `ModerationDashboard`, `QueueListResponse` (paginated).

- [ ] **Step 4: Implement moderation service**

Create `src/moderation/service.py` with functions:
- `submit_for_moderation(db, content_type, content_id, author_age_tier, content_text, media_ids)` — creates queue entry, routes to pre/post-publish
- `process_queue_entry(db, queue_id, action, moderator_id, reason)` — approve/reject/escalate
- `takedown_content(db, content_type, content_id, reason, moderator_id)` — marks removed
- `list_queue(db, status, pipeline, page, page_size)` — paginated queue listing
- `get_dashboard_stats(db)` — pending count, avg time, severity breakdown
- `create_content_report(db, reporter_id, target_type, target_id, reason)` — user reports

- [ ] **Step 5: Implement moderation router**

Create `src/moderation/router.py` with endpoints:
- POST `/queue` — submit content for moderation
- GET `/queue` — list queue (paginated, filterable by status/pipeline)
- GET `/queue/{id}` — get queue entry detail
- PATCH `/queue/{id}/decide` — approve/reject/escalate
- POST `/takedown` — emergency takedown
- GET `/dashboard` — moderation dashboard stats
- POST `/reports` — user content reports
- GET `/reports` — list reports

Register in `src/main.py`.

- [ ] **Step 6: Update `src/moderation/__init__.py`**

```python
"""Content moderation pipeline module.

Public interface for cross-module communication.
"""
from src.moderation.service import submit_for_moderation, takedown_content

__all__ = ["submit_for_moderation", "takedown_content"]
```

- [ ] **Step 7: Write E2E tests**

Create `tests/e2e/test_moderation.py` — ≥25 tests covering full API flows.

- [ ] **Step 8: Write security tests**

Create `tests/security/test_moderation_security.py` — ≥15 tests: auth required, moderator/admin role needed for queue actions, child cannot access queue, reporter can't see other reports.

- [ ] **Step 9: Run all moderation tests**

Run: `pytest tests/unit/test_moderation.py tests/e2e/test_moderation.py tests/security/test_moderation_security.py -v`
Expected: ≥75 tests PASS (unit ≥35, E2E ≥25, security ≥15)

- [ ] **Step 10: Commit**

```bash
git add src/moderation/ tests/unit/test_moderation.py tests/e2e/test_moderation.py tests/security/test_moderation_security.py src/main.py
git commit -m "feat: add moderation module — pipeline, queue CRUD, takedown, dashboard (P1-A6)"
```

---

## Task 4: Fast-Path Text Classifier (P1-A3)

**Deliverable:** Keyword-based text classification with <100ms p99, hold-and-release queue, async AI fallback.

**Files:**
- Create: `src/moderation/keyword_filter.py`
- Modify: `src/moderation/service.py` (integrate fast-path)
- Test: `tests/unit/test_moderation_keyword.py`
- Test: `tests/e2e/test_moderation_keyword.py`
- Test: `tests/security/test_moderation_security.py` (append)

- [ ] **Step 1: Write unit tests for keyword filter**

Test: exact match, normalized matching (case-insensitive, strip accents), per-tier severity lists, BLOCK/ALLOW/UNCERTAIN outcomes, performance (<100ms for 1000 keywords against 1KB text), batch processing.

≥30 unit tests + ≥5 performance tests.

- [ ] **Step 1b: Write E2E and security tests**

E2E (≥20): submit content via moderation API → keyword filter auto-approves/rejects/escalates.
Security (≥5): rate limiting on submission, auth required, child cannot access filter config.

- [ ] **Step 2: Implement keyword filter**

Create `src/moderation/keyword_filter.py`:
- `KeywordFilter` class with per-severity word lists (critical, high, medium)
- `classify_text(text, age_tier)` → returns `FilterResult(action=BLOCK|ALLOW|UNCERTAIN, matched_keywords, severity)`
- Text normalization: lowercase, strip accents, collapse whitespace
- Young tier: more keywords = uncertain → AI review
- Use set-based lookup for O(1) matching, compiled regex for phrases

- [ ] **Step 3: Integrate into moderation pipeline**

Modify `src/moderation/service.py` → `submit_for_moderation()` calls `keyword_filter.classify_text()` first. If BLOCK → auto-reject. If ALLOW → auto-approve (pre-pub) or pass (post-pub). If UNCERTAIN → queue for AI classification.

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/test_moderation_keyword.py tests/e2e/test_moderation_keyword.py -v`
Expected: ≥60 tests PASS (unit ≥30, perf ≥5, E2E ≥20, security ≥5)

- [ ] **Step 5: Commit**

```bash
git add src/moderation/keyword_filter.py tests/unit/test_moderation_keyword.py tests/e2e/test_moderation_keyword.py src/moderation/service.py
git commit -m "feat: add fast-path keyword classifier — <100ms text moderation (P1-A3)"
```

---

## Task 5: Image Moderation Pipeline (P1-A1)

**Deliverable:** CF Images webhook → Hive/Sensity classification → approve/reject pipeline.

**Files:**
- Create: `src/moderation/image_pipeline.py`
- Test: `tests/unit/test_moderation_image.py`
- Test: `tests/e2e/test_moderation_image.py`
- Test: `tests/security/test_moderation_image_security.py`

- [ ] **Step 1: Write unit tests**

Test: webhook payload parsing, Hive API mock (safe/unsafe/error), Sensity API mock, result mapping to moderation actions, retry on API failure, timeout handling, batch processing.

≥30 unit tests, ≥20 E2E tests (mock external APIs), ≥10 security tests.

- [ ] **Step 2: Implement image pipeline**

Create `src/moderation/image_pipeline.py`:
- `classify_image(cloudflare_image_id, age_tier)` → calls Hive/Sensity, returns classification
- Webhook handler for CF Images ready event
- Result caching (Redis) to avoid re-classification
- Graceful degradation: if Hive unavailable, hold in queue for manual review

- [ ] **Step 3: Add webhook endpoint to router**

Add `POST /webhooks/cloudflare-images` to moderation router.

- [ ] **Step 4: Run tests**

Expected: ≥60 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/moderation/image_pipeline.py tests/unit/test_moderation_image.py tests/e2e/test_moderation_image.py
git commit -m "feat: add image moderation pipeline — CF Images + Hive/Sensity (P1-A1)"
```

---

## Task 6: Video Moderation Pipeline (P1-A2)

**Deliverable:** CF Stream → frame extraction → classification → approve/reject.

**Files:**
- Create: `src/moderation/video_pipeline.py`
- Test: `tests/unit/test_moderation_video.py`
- Test: `tests/e2e/test_moderation_video.py`
- Test: `tests/security/test_moderation_video_security.py`

- [ ] **Step 1: Write unit tests**

Test: frame extraction strategy (every N seconds, key frames), per-frame classification, worst-frame decision, CF Stream webhook handling, video length limits (young=30s, preteen=60s, teen=180s).

≥25 unit tests, ≥15 E2E tests, ≥10 security tests.

- [ ] **Step 2: Implement video pipeline**

Create `src/moderation/video_pipeline.py`:
- `classify_video(cloudflare_stream_id, age_tier)` → extracts frames, classifies each, returns worst result
- Frame extraction at 1fps for first 10s, then every 5s
- Webhook handler for CF Stream ready event

- [ ] **Step 3: Run tests and commit**

Expected: ≥50 tests PASS

```bash
git add src/moderation/video_pipeline.py tests/
git commit -m "feat: add video moderation pipeline — CF Stream frame extraction (P1-A2)"
```

---

## Task 7: Social Risk Models v1 (P1-A4)

**Deliverable:** Detection models for grooming, cyberbullying, and sexting in social content.

**Files:**
- Create: `src/moderation/social_risk.py`
- Test: `tests/unit/test_moderation_social_risk.py`
- Test: `tests/e2e/test_moderation_social_risk.py`

- [ ] **Step 1: Write unit tests**

Test: grooming pattern detection (escalation, flattery + isolation, age-inappropriate language), cyberbullying detection (repeated targeting, exclusion language, threatening), sexting detection (solicitation, image requests, body-related), multi-signal scoring, context-aware classification (friends joking vs stranger grooming).

≥40 unit tests, ≥20 E2E tests.

- [ ] **Step 2: Implement social risk models**

Create `src/moderation/social_risk.py`:
- `classify_social_risk(text, conversation_history, relationship_type, author_age_tier, target_age_tier)` → returns risk scores per category
- Extends existing `src/risk/taxonomy.RISK_CATEGORIES` with social-specific signals
- Pattern-based first pass (keyword + regex), AI second pass for uncertain
- Conversation-level context: considers message history, not just single message

- [ ] **Step 3: Integrate into moderation pipeline**

Modify `src/moderation/service.py` → after keyword filter, run social risk models for chat/DM content.

- [ ] **Step 4: Run tests and commit**

Expected: ≥60 tests PASS

```bash
git add src/moderation/social_risk.py tests/unit/test_moderation_social_risk.py
git commit -m "feat: add social risk models — grooming, cyberbullying, sexting detection (P1-A4)"
```

---

## Task 8: CSAM Detection + NCMEC Reporting (P1-A7)

**Deliverable:** PhotoDNA integration, CyberTipline API, evidence preservation, account suspension, audit trail.

**Files:**
- Create: `src/moderation/csam.py`
- Test: `tests/unit/test_moderation_csam.py`

- [ ] **Step 1: Write unit tests**

Test: PhotoDNA hash matching (mock), NCMEC CyberTipline report submission (mock), evidence preservation (encrypted, immutable), account suspension on match, audit trail creation, false positive handling (manual review), notification to law enforcement contact.

≥20 unit tests, ≥10 E2E tests, ≥10 security tests.

**Critical safety requirement:** CSAM detection runs BEFORE any other moderation step. On match: block content, preserve evidence, submit NCMEC report, suspend account, create audit trail. Zero tolerance — no false negative acceptable.

- [ ] **Step 2: Implement CSAM detection**

Create `src/moderation/csam.py`:
- `check_csam(image_bytes_or_hash)` → PhotoDNA API call, returns match/no-match
- `report_to_ncmec(content_id, evidence, reporter_info)` → CyberTipline API submission
- `preserve_evidence(content_id, content_bytes)` → encrypt and store for law enforcement
- `suspend_account(user_id, reason)` → immediate account suspension
- All operations create `ModerationDecision` audit records
- Runs as first step in pipeline, before age tier routing

- [ ] **Step 3: Integrate as first pipeline step**

Modify `src/moderation/service.py` → `submit_for_moderation()` checks `csam.check_csam()` before any other step for media content.

- [ ] **Step 4: Run tests and commit**

Expected: ≥40 tests PASS

```bash
git add src/moderation/csam.py tests/unit/test_moderation_csam.py
git commit -m "feat: add CSAM detection + NCMEC reporting — PhotoDNA, CyberTipline (P1-A7)"
```

---

## Task 9: Social Module — Feed, Profiles, Follows (P1-H2)

**Deliverable:** `src/social/` — Feed CRUD, profile CRUD, follow/unfollow with age-tier enforcement.

**Files:**
- Create: `src/social/service.py`
- Create: `src/social/router.py`
- Create: `src/social/schemas.py`
- Modify: `src/social/__init__.py`
- Modify: `src/main.py` (register router)
- Test: `tests/unit/test_social.py`
- Test: `tests/e2e/test_social.py`
- Test: `tests/security/test_social_security.py`

- [ ] **Step 1: Write unit tests for social service**

Test profiles: create, get, update, visibility settings.
Test posts: create (with moderation integration), list feed (paginated, chronological), get post detail, delete (soft delete), hashtag extraction.
Test follows: follow, unfollow, accept follow request, block, list followers/following.
Test feed: feed shows followed users' posts, feed excludes blocked users, feed pagination.

≥40 unit tests.

- [ ] **Step 2: Implement social schemas**

Create `src/social/schemas.py` with: `ProfileCreate`, `ProfileUpdate`, `ProfileResponse`, `PostCreate`, `PostResponse`, `PostListResponse`, `FollowRequest`, `FollowResponse`, `FeedResponse`.

- [ ] **Step 3: Implement social service**

Create `src/social/service.py`:
- Profile CRUD with visibility controls
- Post CRUD with automatic moderation submission (calls `moderation.submit_for_moderation()`)
- Hashtag extraction from content (regex `#[a-zA-Z0-9_]+`)
- Follow/unfollow with status management
- Feed assembly: posts from followed users, paginated, with moderation_status filter (only approved posts in feed)
- Age-tier integration: checks `age_tier.check_permission()` before post/follow actions

- [ ] **Step 4: Implement social router**

Create `src/social/router.py` with endpoints per spec:
- Profile: GET/PUT `/profiles/me`, GET `/profiles/{user_id}`
- Posts: POST `/posts`, GET `/posts`, GET `/posts/{id}`, DELETE `/posts/{id}`
- Feed: GET `/feed` (paginated)
- Follows: POST `/follow/{user_id}`, DELETE `/follow/{user_id}`, GET `/followers`, GET `/following`
- Hashtags: GET `/hashtags/trending`

Register in `src/main.py`.

- [ ] **Step 5: Write E2E and security tests**

E2E (≥30): full API flows for profile, posts, feed, follows.
Security (≥15): auth required, cross-group isolation, age-tier enforcement (young can't DM), rate limiting.

- [ ] **Step 6: Run all tests**

Run: `pytest tests/unit/test_social.py tests/e2e/test_social.py tests/security/test_social_security.py -v`
Expected: ≥85 tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/social/ tests/unit/test_social.py tests/e2e/test_social.py tests/security/test_social_security.py src/main.py
git commit -m "feat: add social module — feed, profiles, follows with age-tier enforcement (P1-H2)"
```

---

## Task 10: Contacts Module (P1-H3)

**Deliverable:** `src/contacts/` — Contact requests with parent approval gate.

**Files:**
- Create: `src/contacts/service.py`
- Create: `src/contacts/router.py`
- Create: `src/contacts/schemas.py`
- Modify: `src/contacts/__init__.py`
- Modify: `src/main.py`
- Test: `tests/unit/test_contacts.py`
- Test: `tests/e2e/test_contacts.py`
- Test: `tests/security/test_contacts_security.py`

- [ ] **Step 1: Write unit tests**

Test: send request, accept/reject, parent approval flow (5-12 requires parent OK), block, contact limits per age tier (young=10, preteen=25, teen=100), duplicate request prevention, blocked user can't re-request.

≥20 unit tests.

- [ ] **Step 2: Implement contacts module**

Service: `send_request()`, `respond_to_request()`, `approve_as_parent()`, `block_contact()`, `list_contacts()`, `get_pending_approvals()`

Router: POST `/request/{user_id}`, PATCH `/{id}/respond`, PATCH `/{id}/parent-approve`, POST `/{user_id}/block`, GET `/`, GET `/pending`

- [ ] **Step 3: Write E2E and security tests**

E2E (≥15): full flows including parent approval.
Security (≥10): auth, cross-group, age-tier limits, parent-only approval.

- [ ] **Step 4: Run tests and commit**

Expected: ≥45 tests PASS

```bash
git add src/contacts/ tests/ src/main.py
git commit -m "feat: add contacts module — requests with parent approval gate (P1-H3)"
```

---

## Task 11: Australian Safety Compliance (P1-A5)

**Deliverable:** Yoti AU age verification flow, eSafety reporting pipeline, 24h takedown SLA.

**Files:**
- Modify: `src/integrations/` (Yoti AU flow)
- Create: `src/moderation/esafety.py`
- Test: `tests/unit/test_australian_safety.py`
- Test: `tests/e2e/test_australian_safety.py`

- [ ] **Step 1: Write unit tests**

Test: Yoti AU age verification (different from generic Yoti — AU-specific requirements), eSafety complaint submission, 24h takedown tracking, takedown SLA alerting.

≥20 unit tests, ≥15 E2E tests, ≥10 security tests.

- [ ] **Step 2: Implement Yoti AU flow**

Extend `src/integrations/` with AU-specific Yoti parameters per Australian Online Safety Act requirements. Reference `docs/compliance/australian-online-safety-analysis.md`.

- [ ] **Step 3: Implement eSafety reporting**

Create `src/moderation/esafety.py`:
- `submit_esafety_complaint(content_id, category, evidence)` → eSafety Commissioner API
- `track_takedown_sla(content_id)` → 24h countdown, alerts if approaching deadline
- Dashboard integration for SLA tracking

- [ ] **Step 4: Run tests and commit**

Expected: ≥45 tests PASS

```bash
git add src/integrations/ src/moderation/esafety.py tests/
git commit -m "feat: add Australian safety — Yoti AU, eSafety reporting, 24h SLA (P1-A5)"
```

---

## Task 12: Governance Module — Ohio AI Compliance (P1-S3)

**Deliverable:** `src/governance/` — Policy template generator, AI tool inventory, risk assessment, compliance dashboard.

**Files:**
- Create: `src/governance/service.py`
- Create: `src/governance/router.py`
- Create: `src/governance/schemas.py`
- Modify: `src/governance/__init__.py`
- Modify: `src/main.py`
- Test: `tests/unit/test_governance.py`
- Test: `tests/e2e/test_governance.py`
- Test: `tests/security/test_governance_security.py`

- [ ] **Step 1: Write unit tests**

Test: policy CRUD, template generation from Ohio mandate requirements, AI tool inventory management, risk assessment scoring, audit trail, version history.

≥40 unit tests.

- [ ] **Step 2: Implement governance module**

Service:
- `create_policy(db, school_id, policy_type, content)` — creates versioned policy
- `generate_template(state_code, policy_type)` — Ohio-specific templates
- `add_tool_to_inventory(db, school_id, tool_name, risk_level, approval_status)`
- `run_risk_assessment(db, school_id)` — scores based on tool inventory + policy gaps
- `get_compliance_dashboard(db, school_id)` — aggregated compliance view
- All mutations create `GovernanceAudit` records

Router: CRUD for policies, tools, assessments + dashboard endpoint.

- [ ] **Step 3: Write E2E and security tests**

E2E (≥25): full API flows.
Security (≥10): school_admin role required, cross-school isolation.

- [ ] **Step 4: Run tests and commit**

Expected: ≥75 tests PASS

```bash
git add src/governance/ tests/ src/main.py
git commit -m "feat: add governance module — Ohio AI policy, tool inventory, compliance dashboard (P1-S3)"
```

---

## Task 13: WebSocket Service + Redis Pub/Sub (P1-R1, P1-R2)

**Deliverable:** Separate WebSocket FastAPI app with JWT auth, connection management, heartbeat, Redis pub/sub bridge.

**Files:**
- Create: `src/realtime/main.py`
- Create: `src/realtime/auth.py`
- Create: `src/realtime/connections.py`
- Create: `src/realtime/pubsub.py`
- Test: `tests/unit/test_realtime.py`

- [ ] **Step 1: Write unit tests**

Test: JWT validation (valid/expired/missing), connection lifecycle (connect/disconnect/heartbeat), heartbeat timeout, Redis pub/sub message routing, connection limits, multi-room support.

≥35 unit tests, ≥15 WS E2E tests, ≥10 security tests, ≥10 integration tests.

- [ ] **Step 2: Implement WebSocket auth**

Create `src/realtime/auth.py`:
- `validate_ws_token(token)` → validates JWT using same SECRET_KEY as monolith
- Extracts user_id, group_id, role, permissions from token
- Returns `None` for invalid tokens (WebSocket close, not HTTP error)

- [ ] **Step 3: Implement connection manager**

Create `src/realtime/connections.py`:
- `ConnectionManager` class: per-user connections, room-based messaging
- `connect(websocket, user_id)` → register, send welcome
- `disconnect(user_id)` → cleanup, update presence
- `broadcast(room, message)` → send to all room members
- `send_to_user(user_id, message)` → direct delivery
- Heartbeat: ping every 30s, disconnect after 90s silence

- [ ] **Step 4: Implement Redis pub/sub**

Create `src/realtime/pubsub.py`:
- `EventBridge` class: subscribes to Redis channels, dispatches to connections
- Channels: `alerts:{group_id}`, `social:{user_id}`, `moderation:{content_id}`
- Monolith publishes events; WebSocket service consumes and delivers

- [ ] **Step 5: Implement WebSocket FastAPI app**

Create `src/realtime/main.py`:
- Separate FastAPI app (deployed as own Render service per ADR-008)
- WebSocket endpoint `/ws` with token query param
- Connection pool: lazy DB acquisition (per ADR-008 constraint — max 10 connections)
- Structured logging with same `structlog` pattern as monolith

- [ ] **Step 6: Run tests and commit**

Expected: ≥70 tests PASS

```bash
git add src/realtime/ tests/unit/test_realtime.py
git commit -m "feat: add WebSocket service — JWT auth, connection manager, Redis pub/sub (P1-R1, P1-R2)"
```

---

## Task 14: Push Notification Relay + Presence (P1-R3, P1-R4)

**Deliverable:** Expo push token registration, notification delivery, online/offline/last-seen via Redis.

**Files:**
- Create: `src/realtime/notifications.py`
- Create: `src/realtime/presence.py`
- Test: `tests/unit/test_realtime_presence.py`

- [ ] **Step 1: Write unit tests**

Test push: token registration, delivery to Expo push service (mock), batch delivery, failure handling, duplicate token prevention.
Test presence: set online, set offline, get last-seen, list online users in group, auto-offline on disconnect.

≥20 unit tests (push ≥10, presence ≥10), ≥10 E2E tests.

- [ ] **Step 2: Implement push notification relay**

Create `src/realtime/notifications.py`:
- `register_push_token(user_id, expo_push_token)` → stores in Redis
- `send_push(user_id, title, body, data)` → Expo Push API call
- `send_push_batch(user_ids, title, body, data)` → batch delivery
- Integrates with monolith alerts: when alert created → publish to Redis → WS service sends push

- [ ] **Step 3: Implement presence system**

Create `src/realtime/presence.py`:
- `set_online(user_id)` → Redis SET with TTL (5 minutes, refreshed on heartbeat)
- `set_offline(user_id)` → Redis DEL + SET last_seen
- `get_presence(user_id)` → online/offline + last_seen timestamp
- `get_online_users(group_id)` → list of online users in a group
- Auto-offline: when heartbeat expires (Redis key TTL), user goes offline

- [ ] **Step 4: Run tests and commit**

Expected: ≥30 tests PASS

```bash
git add src/realtime/notifications.py src/realtime/presence.py tests/unit/test_realtime_presence.py
git commit -m "feat: add push notification relay + presence system (P1-R3, P1-R4)"
```

---

## Task 15: Mobile shared-auth + shared-api + shared-types Enhancement (P1-M1, P1-M2)

**Deliverable:** SecureStore token storage, biometric unlock, session refresh, WebSocket client, offline queue, retry logic. Also create new type definition files for social, safety, and moderation domains.

**Files:**
- Create: `mobile/packages/shared-auth/src/secure-store.ts`
- Create: `mobile/packages/shared-auth/src/biometric.ts`
- Create: `mobile/packages/shared-auth/src/session.ts`
- Modify: `mobile/packages/shared-auth/src/token-manager.ts`
- Create: `mobile/packages/shared-api/src/ws-client.ts`
- Create: `mobile/packages/shared-api/src/offline-queue.ts`
- Modify: `mobile/packages/shared-api/src/rest-client.ts`
- Test: `mobile/packages/shared-auth/__tests__/secure-store.test.ts`
- Test: `mobile/packages/shared-auth/__tests__/biometric.test.ts`
- Test: `mobile/packages/shared-auth/__tests__/session.test.ts`
- Test: `mobile/packages/shared-api/__tests__/ws-client.test.ts`
- Test: `mobile/packages/shared-api/__tests__/offline-queue.test.ts`

- [ ] **Step 1: Write tests for SecureStore adapter**

Test: store token, retrieve token, clear token, fallback to in-memory when SecureStore unavailable (web/test), migration from in-memory to SecureStore.

≥8 tests.

- [ ] **Step 2: Implement SecureStore adapter**

Create `secure-store.ts` — wraps `expo-secure-store` with fallback.

- [ ] **Step 3: Write tests for biometric**

Test: check availability, prompt for unlock, handle denial, handle not-enrolled.

≥5 tests.

- [ ] **Step 4: Implement biometric unlock**

Create `biometric.ts` — wraps `expo-local-authentication`.

- [ ] **Step 5: Write tests for session management**

Test: auto-refresh before expiry, refresh failure → logout, concurrent refresh dedup.

≥7 tests.

- [ ] **Step 6: Implement session management**

Create `session.ts` — token refresh logic, expiry monitoring, auto-logout.

- [ ] **Step 7: Update token-manager to use SecureStore**

Modify `token-manager.ts` — swap in-memory storage for SecureStore adapter.

- [ ] **Step 8: Write tests for WebSocket client**

Test: connect, disconnect, reconnect on failure, message send/receive, auth token inclusion, heartbeat.

≥10 tests.

- [ ] **Step 9: Implement WebSocket client**

Create `ws-client.ts` — connects to `src/realtime/` WS service, auto-reconnect, typed messages.

- [ ] **Step 10: Write tests for offline queue**

Test: queue request when offline, replay when online, ordering preserved, max queue size.

≥7 tests.

- [ ] **Step 11: Implement offline queue**

Create `offline-queue.ts` — queues failed requests, replays on connectivity restore.

- [ ] **Step 12: Update rest-client with retry logic**

Modify `rest-client.ts` — add retry with exponential backoff, request/response interceptors, offline queue integration.

- [ ] **Step 13: Run all package tests**

Run: `cd mobile && npx turbo run test --filter=@bhapi/auth --filter=@bhapi/api`
Expected: ≥50 tests PASS (auth ≥25, api ≥25)

- [ ] **Step 14: Commit**

```bash
git add mobile/packages/shared-auth/ mobile/packages/shared-api/
git commit -m "feat: enhance shared-auth + shared-api — SecureStore, biometrics, WS client, offline queue (P1-M1, P1-M2)"
```

---

## Task 16: Mobile shared-i18n Enhancement + shared-ui Components (P1-M3, P1-M4)

**Deliverable:** Extended i18n strings for safety/social apps, core UI component library.

**Files:**
- Modify: `mobile/packages/shared-i18n/locales/*.json`
- Modify: `mobile/packages/shared-ui/src/index.ts`
- Create: `mobile/packages/shared-ui/src/BhapiLogo.tsx`
- Create: `mobile/packages/shared-ui/src/Button.tsx`
- Create: `mobile/packages/shared-ui/src/Card.tsx`
- Create: `mobile/packages/shared-ui/src/Input.tsx`
- Create: `mobile/packages/shared-ui/src/Badge.tsx`
- Create: `mobile/packages/shared-ui/src/Toast.tsx`
- Create: `mobile/packages/shared-ui/src/Avatar.tsx`
- Test: `mobile/packages/shared-ui/__tests__/Button.test.tsx`
- Test: `mobile/packages/shared-ui/__tests__/Card.test.tsx`
- (tests for each component)

- [ ] **Step 1: Extend i18n locale files**

Add safety and social app strings to all 6 locale files: dashboard labels, alert types, post actions, moderation messages, onboarding flow, settings labels.

≥10 i18n tests.

- [ ] **Step 2: Write component tests**

Write tests for each UI component:
- BhapiLogo: renders PNG, correct dimensions, accessible
- Button: primary/secondary/outline variants, sizes (sm/md/lg), isLoading state, disabled state, 44pt minimum tap target
- Card: renders children, shadow, rounded corners
- Input: value/onChange, placeholder, error state, label, secure text
- Badge: variants (info/success/warning/error), text rendering
- Toast: show/hide, auto-dismiss, variants
- Avatar: image source, fallback initials, size variants

≥30 component tests.

- [ ] **Step 3: Implement all UI components**

Use React Native + `@bhapi/config` theme. All components must meet WCAG 2.1 AA: 44pt tap targets, proper accessibility labels, sufficient contrast (primary-600 for buttons per portal convention).

- [ ] **Step 4: Run tests**

Run: `cd mobile && npx turbo run test --filter=@bhapi/ui --filter=@bhapi/i18n`
Expected: ≥40 tests PASS (i18n ≥10, ui ≥30)

- [ ] **Step 5: Commit**

```bash
git add mobile/packages/shared-i18n/ mobile/packages/shared-ui/
git commit -m "feat: add shared-ui components + extend i18n — Button, Card, Input, Badge, Toast, Avatar (P1-M3, P1-M4)"
```

---

## Task 17: Safety App — Auth Screens (P1-M5)

**Deliverable:** Login, register, magic link, email verification screens.

**Files:**
- Create: `mobile/apps/safety/app/_layout.tsx`
- Create: `mobile/apps/safety/app/(auth)/login.tsx`
- Create: `mobile/apps/safety/app/(auth)/register.tsx`
- Create: `mobile/apps/safety/app/(auth)/magic-link.tsx`
- Create: `mobile/apps/safety/app/(auth)/_layout.tsx`
- Test: `mobile/apps/safety/__tests__/auth/`

- [ ] **Step 1: Write component tests**

Test: login form renders, submit calls API, validation errors displayed, magic link flow, registration with privacy_notice_accepted, email verification status.

≥15 component tests, ≥10 integration tests.

- [ ] **Step 2: Implement root layout**

Replace placeholder `app/index.tsx` with Expo Router layout:
- Auth guard (redirect to login if not authenticated)
- Tab navigation for authenticated users
- Theme provider from `@bhapi/config`

- [ ] **Step 3: Implement auth screens**

- Login: email + password, magic link option, forgot password link
- Register: email, password, display_name, account_type, `privacy_notice_accepted: true`
- Magic link: email input → "Check your email" screen → deep link handler
- Uses `@bhapi/api` rest client, `@bhapi/auth` token manager

- [ ] **Step 4: Run tests and commit**

Expected: ≥25 tests PASS

```bash
git add mobile/apps/safety/
git commit -m "feat: add Safety app auth screens — login, register, magic link (P1-M5)"
```

---

## Task 18: Safety App — Dashboard + Alerts (P1-M6, P1-M7)

**Deliverable:** Activity summary, risk overview, recent alerts, platform breakdown, alert list/detail/snooze/escalation.

**Files:**
- Create: `mobile/apps/safety/app/(dashboard)/index.tsx`
- Create: `mobile/apps/safety/app/(dashboard)/alerts.tsx`
- Create: `mobile/apps/safety/app/(dashboard)/alert-detail.tsx`
- Create: `mobile/apps/safety/app/(dashboard)/_layout.tsx`
- Test: `mobile/apps/safety/__tests__/dashboard/`

- [ ] **Step 1: Write component tests**

Dashboard: renders activity summary, risk overview chart, recent alerts list, platform breakdown, loading state, error state, degraded section handling.
Alerts: list with severity badges, detail view, snooze action, escalation action, pull-to-refresh.

≥60 component + integration tests (dashboard: ≥20 component + ≥15 integration = 35; alerts: ≥15 component + ≥10 integration = 25).

- [ ] **Step 2: Implement dashboard**

- Calls `GET /api/v1/portal/dashboard` (existing endpoint)
- Activity summary card, risk severity distribution, recent alerts carousel, platform usage pie chart
- Degraded section handling (shows amber warning if API returns `degraded_sections`)

- [ ] **Step 3: Implement alerts screens**

- Alert list: paginated, filterable by severity, sortable by date
- Alert detail: full context, action buttons (snooze, escalate, dismiss)
- Snooze: duration picker, calls `PATCH /api/v1/alerts/{id}`
- Escalation: confirmation dialog, calls escalation endpoint

- [ ] **Step 4: Run tests and commit**

Expected: ≥60 tests PASS

```bash
git add mobile/apps/safety/app/(dashboard)/ mobile/apps/safety/__tests__/
git commit -m "feat: add Safety app dashboard + alerts — activity summary, risk overview, alert management (P1-M6, P1-M7)"
```

---

## Task 19: Safety App — Group Management + Push Notifications (P1-M8, P1-M9)

**Deliverable:** Member management, invitations, consent, push notifications.

**Files:**
- Create: `mobile/apps/safety/app/(children)/index.tsx`
- Create: `mobile/apps/safety/app/(settings)/index.tsx`
- Test: `mobile/apps/safety/__tests__/children/`
- Test: `mobile/apps/safety/__tests__/settings/`

- [ ] **Step 1: Write component tests**

Groups: member list, add member form, invitation flow, consent status display.
Push: permission request, token registration, notification display.

≥40 component + integration tests (groups: ≥15 component + ≥10 integration = 25; push: ≥10 unit + ≥5 integration = 15).

- [ ] **Step 2: Implement group management screens**

- Member list with role badges (parent, child)
- Add member flow: email invite → pending state → acceptance
- Consent status per child (COPPA/GDPR/LGPD)
- Family member cap enforcement (MAX_FAMILY_MEMBERS = 5)

- [ ] **Step 3: Implement push notifications**

- Expo Notifications setup (permission request, token registration)
- Token sent to `POST /api/v1/alerts/push-token` (or new endpoint on realtime service)
- Foreground notification display
- Deep linking from notification tap to alert detail

- [ ] **Step 4: Run tests and commit**

Expected: ≥40 tests PASS

```bash
git add mobile/apps/safety/
git commit -m "feat: add Safety app groups + push notifications (P1-M8, P1-M9)"
```

---

## Task 20: Social App Screen Shells + shared-ui Social Components (P1-H5, P1-H6)

**Deliverable:** Social app navigation structure with screen shells (feed, profile, chat, settings, onboarding), plus social-specific shared-ui components.

**Files:**
- Create: `mobile/apps/social/app/_layout.tsx`
- Create: `mobile/apps/social/app/(auth)/login.tsx`
- Create: `mobile/apps/social/app/(feed)/index.tsx`
- Create: `mobile/apps/social/app/(chat)/index.tsx`
- Create: `mobile/apps/social/app/(profile)/index.tsx`
- Create: `mobile/apps/social/app/(settings)/index.tsx`
- Create: `mobile/packages/shared-ui/src/PostCard.tsx`
- Create: `mobile/packages/shared-ui/src/MessageBubble.tsx`
- Create: `mobile/packages/shared-ui/src/ContactRequest.tsx`
- Create: `mobile/packages/shared-ui/src/CommentThread.tsx`
- Test: various

- [ ] **Step 1: Write component tests**

Social UI components: PostCard (author avatar, content, like/comment counts, moderation badge), CommentThread (nested, author, timestamp), MessageBubble (sent/received, timestamp, read receipt), ContactRequest (accept/reject buttons, requester info).
Screen shells: renders without crash, navigation works, age-tier guard.

≥35 tests (component ≥15, screen shells ≥20).

- [ ] **Step 2: Implement shared-ui social components**

- PostCard: avatar, display name, content text, media preview, like/comment counts, time ago, moderation status badge (pending/approved)
- CommentThread: list of comments with author, nesting support
- MessageBubble: sent (right, primary color) vs received (left, neutral), timestamp
- ContactRequest: requester info, accept/reject buttons, parent approval pending indicator

- [ ] **Step 3: Implement social app screen shells**

- Root layout with age-tier guard (reads tier from auth context, adjusts UI)
- Tab navigation: Feed, Chat, Profile, Settings
- Each screen: shell with loading state, pulls from respective API endpoint
- Feed screen: uses PostCard, pull-to-refresh, infinite scroll placeholder
- Chat screen: conversation list placeholder
- Profile screen: avatar, display name, follower/following counts
- Settings screen: notification preferences, language, privacy

- [ ] **Step 4: Run tests and commit**

Expected: ≥35 tests PASS

```bash
git add mobile/apps/social/ mobile/packages/shared-ui/
git commit -m "feat: add social app screen shells + PostCard, MessageBubble, ContactRequest (P1-H5, P1-H6)"
```

---

## Task 21: Google Admin Console Integration (P1-S1)

**Deliverable:** Mass extension deployment via Google Admin Console for schools.

**Files:**
- Create: `extension/src/google-admin.ts`
- Modify: `extension/manifest.json` (enterprise policies)
- Create: `src/integrations/google_admin.py`
- Test: `tests/unit/test_google_admin.py`
- Test: `tests/e2e/test_google_admin.py`

- [ ] **Step 1: Write unit tests**

Test: extension policy configuration, managed storage API, force-install configuration, device inventory reporting, group policy application.

≥30 unit tests, ≥20 E2E tests, ≥10 security tests.

- [ ] **Step 2: Implement backend for Google Admin**

Create `src/integrations/google_admin.py`:
- Integration with Google Admin SDK for device management
- Extension deployment status tracking per device
- Policy push to managed Chrome browsers
- Device inventory endpoint for school IT dashboard

- [ ] **Step 3: Implement extension enterprise support**

Modify extension manifest for managed installations:
- `storage.managed_schema.json` for admin-configurable settings
- Enterprise policy enforcement (school can set monitoring level)
- Auto-configuration on managed install

- [ ] **Step 4: Run tests and commit**

Expected: ≥60 tests PASS

```bash
git add extension/ src/integrations/google_admin.py tests/
git commit -m "feat: add Google Admin Console integration for school extension deployment (P1-S1)"
```

---

## Task 22: School IT Admin Dashboard (P1-S2)

**Deliverable:** Device inventory, deployment status, policy management dashboard.

**Files:**
- Create: `portal/src/app/(dashboard)/school-admin/page.tsx`
- Create: `portal/src/hooks/use-school-admin.ts`
- Modify: `portal/messages/*.json` (school admin strings)
- Test: `portal/src/app/(dashboard)/school-admin/__tests__/`

- [ ] **Step 1: Write component tests**

Test: device inventory table, deployment status indicators, policy management form, filter/search, export functionality.

≥20 unit tests, ≥15 E2E tests, ≥10 security tests.

- [ ] **Step 2: Implement school admin page**

- Device inventory table with status (deployed/pending/error)
- Deployment progress bar (X of Y devices)
- Policy management: create/edit/apply policies
- Search/filter devices by status, OS, last-seen
- Export device list as CSV

- [ ] **Step 3: Run tests and commit**

Expected: ≥45 tests PASS

```bash
git add portal/src/app/\(dashboard\)/school-admin/ portal/src/hooks/ portal/messages/
git commit -m "feat: add school IT admin dashboard — device inventory, deployment, policies (P1-S2)"
```

---

## Task 23: Chromebook-Optimized Extension (P1-S4)

**Deliverable:** Extension optimized for Chromebook with offline capability.

**Files:**
- Create: `extension/src/offline-cache.ts`
- Create: `extension/src/school-policy.ts`
- Modify: `extension/manifest.json`
- Test: `extension/__tests__/offline-cache.test.ts`
- Test: `extension/__tests__/school-policy.test.ts`

- [ ] **Step 1: Write tests**

Test: offline event caching (IndexedDB), sync on reconnect, Chromebook-specific optimizations (memory, CPU), school policy enforcement, managed storage read.

≥15 unit tests, ≥10 E2E tests.

- [ ] **Step 2: Implement offline cache**

Create `extension/src/offline-cache.ts`:
- IndexedDB storage for capture events when offline
- Batch sync when connectivity restored
- Max cache size (1000 events) with FIFO eviction
- Sync status indicator in extension popup

- [ ] **Step 3: Implement school policy enforcement**

Create `extension/src/school-policy.ts`:
- Reads from `chrome.storage.managed` (admin-configured)
- Enforces monitoring level (standard/enhanced/maximum)
- Respects school schedule (monitor during school hours only)
- Network-aware: different behavior on school vs home network

- [ ] **Step 4: Run tests and commit**

Expected: ≥25 tests PASS

```bash
git add extension/
git commit -m "feat: add Chromebook optimization — offline cache, school policy enforcement (P1-S4)"
```

---

## Task 24: Compliance Reporting — School Board PDF Export (P1-S5)

**Deliverable:** School board compliance report PDF generator.

**Files:**
- Modify: `src/reporting/service.py` (add school board report type)
- Modify: `src/reporting/router.py` (new endpoint)
- Test: `tests/unit/test_compliance_reporting.py`

- [ ] **Step 1: Write tests**

Test: report generation with governance data, PDF rendering (ReportLab — unique style names per CLAUDE.md), Ohio-specific template, data aggregation, date range filtering.

≥10 unit tests, ≥5 E2E tests.

- [ ] **Step 2: Implement school board report**

Add school board report type to existing reporting module:
- Aggregates governance policy compliance data
- AI tool inventory summary
- Risk assessment results
- Student safety metrics (anonymized)
- PDF export using existing ReportLab infrastructure

- [ ] **Step 3: Run tests and commit**

Expected: ≥15 tests PASS

```bash
git add src/reporting/ tests/unit/test_compliance_reporting.py
git commit -m "feat: add school board compliance PDF export (P1-S5)"
```

---

## Task 25: Chrome Web Store Enterprise Listing (P1-S6)

**Deliverable:** Submit extension to Chrome Web Store with enterprise listing.

**No code changes** — operational task.

- [ ] **Step 1: Prepare CWS listing materials**

- Screenshots (5+ showing monitoring in action)
- Description (enterprise-focused, compliance keywords)
- Privacy policy URL (bhapi.ai/legal/privacy-policy)
- Categories: Education, Productivity

- [ ] **Step 2: Submit to Chrome Web Store**

- Submit via Chrome Web Store Developer Dashboard
- Request enterprise listing (unlisted, available via admin console)
- Verify managed storage schema included in submission

- [ ] **Step 3: Document submission**

Record submission ID, expected review timeline, listing URL (once approved).

---

## Task 26: Trust & Safety Operations + School Procurement (P1-A8, P1-A9)

**Deliverable:** Documentation — T&S ops doc, FERPA compliance, SDPA template, vendor security questionnaire.

**No code changes** — documentation task.

- [ ] **Step 1: Write Trust & Safety Operations Document**

Create `docs/operations/trust-safety-operations.md`:
- Content moderation escalation procedures
- CSAM response protocol (per NCMEC requirements)
- User report handling SLA
- Moderator training requirements
- Appeal process
- Law enforcement cooperation guidelines

- [ ] **Step 2: Write FERPA Compliance Documentation**

Create `docs/compliance/ferpa-compliance.md`:
- Data handling practices for student records
- School official exception documentation
- Data deletion procedures
- Annual notification template

- [ ] **Step 3: Create School Procurement Package**

Create `docs/procurement/`:
- `sdpa-template.md` — Student Data Privacy Agreement template
- `vendor-security-questionnaire.md` — Pre-filled security questionnaire
- `quote-po-workflow.md` — Quote/PO/invoicing process
- `insurance-certificate.md` — Cyber liability insurance details

- [ ] **Step 4: Commit**

```bash
git add docs/operations/ docs/compliance/ferpa-compliance.md docs/procurement/
git commit -m "docs: add T&S operations, FERPA compliance, school procurement package (P1-A8, P1-A9)"
```

---

## Task 27: TestFlight + Android Internal Testing (P1-M10)

**Deliverable:** Safety app deployed to TestFlight and Android internal testing track.

**Depends on:** Tasks 17-19 (Safety app screens complete)

**Files:**
- Create: `mobile/apps/safety/eas.json` (EAS Build config)
- Create: `mobile/maestro/safety-smoke.yaml` (Maestro E2E)
- Modify: `mobile/apps/safety/app.json` (version, build number)

- [ ] **Step 1: Write Maestro E2E tests**

Create `mobile/maestro/safety-smoke.yaml`:
- App launch → login screen renders
- Login flow → dashboard renders
- Navigate to alerts tab
- Navigate to children tab
- Navigate to settings
- Pull-to-refresh on dashboard
- Alert detail navigation
- Logout flow

≥10 Maestro E2E tests.

- [ ] **Step 2: Configure EAS Build**

Create `mobile/apps/safety/eas.json`:
- Development profile (simulator builds)
- Preview profile (internal testing)
- Production profile (App Store/Play Store submission)
- Environment variables: API_URL, WS_URL

- [ ] **Step 3: Build and submit**

```bash
cd mobile/apps/safety
npx eas build --platform ios --profile preview
npx eas submit --platform ios --profile preview  # TestFlight
npx eas build --platform android --profile preview
# Upload to Play Console internal testing track
```

- [ ] **Step 4: Verify TestFlight + Android internal builds**

- Install on test device from TestFlight
- Install on test device from Play Console internal track
- Run Maestro smoke tests on both platforms

- [ ] **Step 5: Commit**

```bash
git add mobile/apps/safety/eas.json mobile/maestro/
git commit -m "feat: add Safety app TestFlight + Android internal testing (P1-M10)"
```

---

## Task 28: Media Module — Cloudflare R2/Images/Stream (P1 media)

**Deliverable:** `src/media/` — Upload, resize, transcode orchestration via Cloudflare.

**Files:**
- Create: `src/media/__init__.py`, `src/media/router.py`, `src/media/service.py`, `src/media/models.py`, `src/media/schemas.py`
- Modify: `src/main.py` (register router)
- Modify: `alembic/env.py` (import MediaAsset)
- Test: `tests/unit/test_media.py`, `tests/e2e/test_media.py`, `tests/security/test_media_security.py`

- [ ] **Step 1: Write unit tests**

Test: upload URL generation (presigned R2), image variant creation (CF Images), video transcode initiation (CF Stream), webhook handling, media status tracking, ownership validation, size limits per age tier.

≥25 unit tests, ≥15 E2E tests, ≥10 security tests.

- [ ] **Step 2: Implement media module**

Service:
- `create_upload_url(db, owner_id, media_type, content_length)` → presigned R2 upload URL
- `register_media(db, owner_id, cloudflare_id, media_type)` → create MediaAsset record
- `get_variants(db, media_id)` → return processed variants (thumbnails, resized)
- `handle_image_webhook(payload)` → CF Images ready callback
- `handle_video_webhook(payload)` → CF Stream ready callback

Router: POST `/upload`, GET `/{id}`, GET `/{id}/variants`, POST `/webhooks/images`, POST `/webhooks/stream`

MediaAsset model owns all media metadata; moderation module references it for classification.

- [ ] **Step 3: Run tests and commit**

Expected: ≥50 tests PASS

```bash
git add src/media/ tests/unit/test_media.py tests/e2e/test_media.py tests/security/test_media_security.py src/main.py alembic/env.py
git commit -m "feat: add media module — CF R2/Images/Stream upload, resize, transcode (P1 media)"
```

---

## Task 29: Messaging Module — Skeleton (P1 messaging)

**Deliverable:** `src/messaging/` — Basic conversation and message CRUD (full real-time chat UX deferred to Phase 2 P2-S4).

**Files:**
- Create: `src/messaging/__init__.py`, `src/messaging/router.py`, `src/messaging/service.py`, `src/messaging/models.py`, `src/messaging/schemas.py`
- Create: `alembic/versions/037_messaging.py`
- Modify: `src/main.py` (register router)
- Modify: `alembic/env.py` (import models)
- Test: `tests/unit/test_messaging.py`, `tests/e2e/test_messaging.py`

- [ ] **Step 1: Write unit tests**

Test: create conversation, add members, send text message, list conversations, list messages (paginated), mark as read, age-tier enforcement (young can't message).

≥20 unit tests, ≥15 E2E tests.

- [ ] **Step 2: Create models**

`Conversation` (type=direct/group, created_by, title), `ConversationMember` (conversation_id, user_id, last_read_at, role), `Message` (conversation_id, sender_id, content, message_type, moderation_status), `MessageMedia` (message_id, cloudflare_id, media_type, moderation_status).

- [ ] **Step 3: Create migration**

Run: `alembic revision --autogenerate -m "messaging conversations and messages"`

- [ ] **Step 4: Implement service + router**

Service: `create_conversation()`, `send_message()` (integrates with moderation pipeline), `list_conversations()`, `list_messages()`, `mark_read()`
Router: POST `/conversations`, GET `/conversations`, GET `/conversations/{id}/messages`, POST `/conversations/{id}/messages`, PATCH `/conversations/{id}/read`

Note: Real-time delivery via WebSocket is Phase 2 (P2-S4). This skeleton provides REST CRUD so the social app chat screen shell has an API to call.

- [ ] **Step 5: Run tests and commit**

Expected: ≥35 tests PASS

```bash
git add src/messaging/ alembic/ tests/unit/test_messaging.py tests/e2e/test_messaging.py src/main.py
git commit -m "feat: add messaging module skeleton — conversation + message CRUD (P1 messaging)"
```

---

## Task 30: School Pilot Outreach + Onboarding (P1-S7)

**Deliverable:** First school pilot identified with onboarding started.

**No code changes** — operational task.

- [ ] **Step 1: Identify target pilot school**

Criteria: US-based, Ohio preferred (AI mandate), 200-1000 students, Chromebook fleet, willing IT admin contact.

- [ ] **Step 2: Prepare onboarding materials**

- School-specific configuration guide
- IT admin setup walkthrough
- Google Admin Console deployment instructions
- Extension configuration for school policies
- Parent communication template

- [ ] **Step 3: Schedule kickoff meeting**

- Demo the governance dashboard (Task 12)
- Walk through Chromebook deployment (Task 25)
- Set up school account in production
- Define success metrics (deployment %, usage rate, admin satisfaction)

- [ ] **Step 4: Document pilot**

Record: school name, contact, deployment date, student count, success criteria, feedback channel.

---

## Exit Criteria Verification

After all tasks complete, verify:

- [ ] Chrome Web Store enterprise listing live (Task 25)
- [ ] Ohio governance MVP deployed and demo-ready (Task 12)
- [ ] ≥1 school pilot onboarding (Task 30)
- [ ] Safety app in TestFlight + Android internal testing (Task 27)
- [ ] Pre-publish moderation pipeline: <2s p95, image pipeline functional (Tasks 3-6)
- [ ] All social backend APIs functional with full test coverage (Tasks 9-10, 28-29)
- [ ] Social app screen shells navigable with shared-ui components (Task 20)
- [ ] eSafety reporting pipeline live (Task 11)
- [ ] WebSocket service deployed with presence working (Tasks 13-14)
- [ ] Test count: ≥2,549 (current ~1,887 + target ~1,200 new including media/messaging)
- [ ] Security test coverage: 100% of new endpoints have auth/RBAC/age-tier tests
- [ ] All Alembic migrations (032-038) committed and pushed

**Final verification commands:**

```bash
# Backend tests
pytest tests/ -v --tb=short

# Frontend tests
cd portal && npx vitest run

# Mobile tests
cd mobile && npx turbo run test

# Count total tests
pytest tests/ --co -q | tail -1
cd portal && npx vitest run 2>&1 | grep "Tests"
cd mobile && npx turbo run test 2>&1 | grep "Tests"
```
