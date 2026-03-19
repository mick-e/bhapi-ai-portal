# Content Moderation Pipeline — Technical Design Document

**Version:** 1.0
**Date:** March 19, 2026
**Status:** Draft
**Author:** Platform Engineering
**Depends on:** Design Spec Section 4 (Content Moderation Architecture), Section 14 (CSAM/NCMEC)

---

## 1. Pipeline Overview

The content moderation pipeline extends the existing `src/risk/` module to support social content (posts, comments, messages, media) in addition to AI conversation capture events. It introduces age-tier-aware routing that determines whether content enters a pre-publish hold queue or goes live immediately with post-publish monitoring.

### End-to-End Flow

```
Content Submitted (post/comment/message/media)
         |
         v
+-------------------------------+
|  1. CSAM PRE-CHECK (media)    |   <-- PhotoDNA hash match, runs BEFORE anything else
|     Image/video only           |   <-- On match: block, preserve, NCMEC report, suspend
+-------------------------------+
         |
         | (clean or text-only)
         v
+-------------------------------+
|  2. AGE TIER ROUTER           |
|     Reads age_tier_configs     |
|     .tier for the author       |
|                                |
|  5-9:   ALL pre-publish        |
|  10-12: text=post-pub,         |
|         image/video=pre-pub    |
|  13-15: ALL post-publish       |
+-------------------------------+
         |
    +----+----+
    v         v
PRE-PUBLISH   POST-PUBLISH
    |              |
    v              v
+----------+  +-----------+
| Hold in  |  | Publish   |
| moderation|  | immediately|
| _queue   |  | to feed   |
| status=  |  |           |
| pending  |  |           |
+----+-----+  +-----+----+
     |              |
     v              v
+-------------------------------+
|  3. FAST-PATH KEYWORD CHECK   |   <-- <100ms p99
|     Normalized text matching   |
|     Per-tier severity lists    |
|                                |
|  BLOCK  --> reject immediately |
|  ALLOW  --> approve (pre-pub)  |
|             or pass (post-pub) |
|  UNCERTAIN --> continue to AI  |
+-------------------------------+
         |
         v
+-------------------------------+
|  4. AI CLASSIFICATION          |   <-- Vertex AI / keyword fallback
|     14-category risk taxonomy  |   <-- Reuses src/risk/safety_classifier
|     Score 0-100 per category   |
|                                |
|  Image: Hive/Sensity via CF   |
|  Video: frame extract + Hive  |
+-------------------------------+
         |
    +----+----+
    v         v
 APPROVE    REJECT/ESCALATE
    |              |
    v              v
Pre-pub:       Parent notified
 release       Alert created
 content       Content removed/held
               Moderation queue entry
Post-pub:      Appeal flow available
 content
 already
 visible
```

### Integration with Existing `src/risk/` Module

The moderation pipeline does NOT replace the existing risk pipeline in `src/risk/pipeline.py`. They serve different purposes:

| Concern | `src/risk/` (existing) | `src/moderation/` (new) |
|---------|----------------------|------------------------|
| **Input** | `CaptureEvent` (AI conversation monitoring) | Social content (posts, comments, messages, media) |
| **Pipeline** | PII detection, safety classification, rules engine, deepfake detection | Age-tier routing, keyword fast-path, AI classification, image/video moderation |
| **Output** | `RiskEvent` + `Alert` | `ModerationQueue` entry + approve/reject decision |
| **Latency** | Async background processing (seconds to minutes) | Pre-publish: <2s SLA; Post-publish: <60s takedown |
| **Shared** | `src/risk/safety_classifier.classify()`, `src/risk/taxonomy.RISK_CATEGORIES` | Same classifier and taxonomy, called via public `__init__.py` |

The moderation module calls into `src/risk/` via its public interface (`from src.risk import process_event, RiskClassification, RISK_CATEGORIES`) for AI-based text classification. It does NOT duplicate the classifier logic.

---

## 2. Age-Tier Routing

### How Content Enters the Pipeline

When a user submits content through `src/social/` (posts, comments) or `src/messaging/` (messages), the endpoint calls `src/moderation/` before or after persisting the content, depending on the author's age tier.

The tier is read from `age_tier_configs.tier` for the content author. If no tier config exists (should not happen for Social app users), the system defaults to the most restrictive tier (young/5-9).

### Decision Tree

```
Content arrives with author_id
         |
         v
Lookup age_tier_configs WHERE member_id = author.member_id
         |
         v
+------------------+
| tier = "young"   |  (5-9)
| ALL content:     |
|   pre-publish    |
+------------------+

+------------------+
| tier = "preteen" |  (10-12)
| text content:    |
|   post-publish   |
| image/video:     |
|   pre-publish    |
+------------------+

+------------------+
| tier = "teen"    |  (13-15)
| ALL content:     |
|   post-publish   |
+------------------+
```

### Per-Content-Type Matrix

| Content Type | 5-9 (Young) | 10-12 (Pre-teen) | 13-15 (Teen) |
|-------------|:-----------:|:----------------:|:------------:|
| Text post | Pre-publish | Post-publish | Post-publish |
| Text comment | Pre-publish | Post-publish | Post-publish |
| Text message | Pre-publish | Post-publish | Post-publish |
| Image post | Pre-publish | Pre-publish | Post-publish |
| Image message | Pre-publish | Pre-publish | Post-publish |
| Video post | Pre-publish | Pre-publish | Post-publish |
| Video message | Pre-publish | Pre-publish | Post-publish |

### Pre-Publish Behavior

1. Content is persisted to the source table (e.g., `social_posts`) with `moderation_status = 'pending'`.
2. A `moderation_queue` row is created with `pipeline = 'pre_publish'` and `status = 'pending'`.
3. Content is NOT visible in feeds/conversations until `moderation_status` is updated to `'approved'`.
4. The WebSocket `moderation_gate` holds delivery until a decision is made.
5. On approval: source record updated to `moderation_status = 'approved'`, WebSocket delivers content.
6. On rejection: source record updated to `moderation_status = 'rejected'`, author shown "content not posted" message.

### Post-Publish Behavior

1. Content is persisted with `moderation_status = 'published'` (visible immediately).
2. A `moderation_queue` row is created with `pipeline = 'post_publish'` and `status = 'pending'`.
3. If moderation rejects: source record updated to `moderation_status = 'removed'`, content hidden from feeds/conversations, author and parent notified.
4. Takedown SLA: <30s for 10-12 tier, <60s for 13-15 tier.

---

## 3. Fast-Path Keyword Classifier (<100ms)

### Word List Structure

The keyword classifier uses a three-tier severity system with per-age-tier configuration. Lists are loaded at startup and cached in memory (no DB queries on the hot path).

```python
# Conceptual structure — stored in src/moderation/word_lists.py

TIER_WORD_LISTS = {
    "young": {      # 5-9: strictest
        "block": [...],   # Immediate reject, no AI needed
        "flag": [...],    # Hold for AI classification
        "allow": [...],   # Override: words that look bad but are OK for kids
    },
    "preteen": {    # 10-12: moderate
        "block": [...],
        "flag": [...],
        "allow": [...],
    },
    "teen": {       # 13-15: least restrictive
        "block": [...],
        "flag": [...],
        "allow": [...],
    },
}

# Category-specific lists mapping to the 14-category taxonomy
CATEGORY_WORD_LISTS = {
    "SELF_HARM": {
        "block": [r"\b(kill\s+myself|suicide|want\s+to\s+die)\b", ...],
        "flag": [r"\b(self[\-\s]harm|cutting)\b", ...],
    },
    "VIOLENCE": { ... },
    "BULLYING_HARASSMENT": { ... },
    "ADULT_CONTENT": { ... },
    "PII_EXPOSURE": { ... },
    # ... all 14 categories from src/risk/taxonomy.py
}
```

### Matching Algorithm

Text normalization pipeline (applied before matching):

1. **Unicode normalization:** NFKD decomposition, strip combining characters (accents).
2. **Leetspeak translation:** `0→o`, `1→i/l`, `3→e`, `4→a`, `5→s`, `@→a`, `$→s`, etc.
3. **Invisible character removal:** zero-width spaces, zero-width joiners, soft hyphens.
4. **Whitespace normalization:** collapse multiple spaces, trim.
5. **Case folding:** lowercase.

Matching modes:
- **Word boundary matching:** `\b` anchored regex for single words.
- **Phrase matching:** Multi-word patterns with flexible whitespace (`\s+` between words).
- **No partial matching:** "class" does not match "classic" (word boundary enforcement).

### Decision Logic

```
normalized_text = normalize(raw_text)

1. Check allow list first (per-tier). If match, skip to ALLOW.
2. Check block list (per-tier). If match, BLOCK immediately.
3. Check flag list (per-tier). If match, UNCERTAIN (continue to AI).
4. Check category block lists (global). If match, BLOCK with category.
5. Check category flag lists (global). If match, UNCERTAIN with category hint.
6. No match → ALLOW (for pre-publish) or PASS (for post-publish, AI still runs).
```

### Hold-and-Release Queue

For pre-publish content, the keyword classifier provides the initial fast decision:

- **BLOCK:** `moderation_queue.status = 'rejected'`, source `moderation_status = 'rejected'`. No further processing.
- **ALLOW:** `moderation_queue.status = 'approved'`, source `moderation_status = 'approved'`. AI classification still runs asynchronously and can downgrade to rejected within the SLA window.
- **UNCERTAIN:** `moderation_queue.status = 'pending'`, content remains held. AI classification runs synchronously (within 2s SLA).

### Performance Target

- **<100ms p99** for the keyword check (normalization + matching).
- Achieved by: in-memory word lists (no DB), compiled regex patterns (cached at startup), no I/O on the hot path.
- Benchmark: 1000 concurrent keyword checks should complete within 100ms each.

---

## 4. AI Classification

### Integration with Existing Safety Classifier

The moderation pipeline reuses the existing `src/risk/safety_classifier.py` for text classification. This classifier supports three modes via the `SAFETY_CLASSIFIER_MODE` environment variable:

| Mode | Behavior |
|------|----------|
| `keyword_only` | Only keyword-based fallback (default for dev/test) |
| `vertex_ai` | Only Vertex AI / Gemini (fails if unavailable) |
| `auto` | Try Vertex AI first, fall back to keywords if unavailable |

The moderation module calls `classify()` from the safety classifier's public interface.

### 14-Category Risk Taxonomy

Each classification produces a score per category. The existing taxonomy from `src/risk/taxonomy.py`:

| Category | Severity | Moderation Action |
|----------|----------|-------------------|
| `SELF_HARM` | critical | Immediate block + parent alert |
| `VIOLENCE` | critical | Immediate block + parent alert |
| `RADICALISATION` | critical | Immediate block + parent alert |
| `CSAM_ADJACENT` | critical | Block + NCMEC + account suspend |
| `ADULT_CONTENT` | high | Block + parent alert |
| `SCAM_MANIPULATION` | high | Block + parent alert |
| `PII_EXPOSURE` | high | Block + parent alert |
| `DEEPFAKE_CONTENT` | high | Block + parent alert |
| `ACADEMIC_DISHONESTY` | medium | Flag + parent notification (batched) |
| `BULLYING_HARASSMENT` | medium | Block + parent notification |
| `SPEND_ANOMALY` | medium | Flag only (not applicable to social content) |
| `EMOTIONAL_DEPENDENCY` | medium | Flag + parent notification (batched) |
| `EXCESSIVE_USAGE` | low | Informational (weekly digest) |
| `UNKNOWN_PLATFORM` | low | Informational (not applicable to social content) |

Social-specific risk categories (added to `src/risk/taxonomy.py` in Phase 1):

| Category | Severity | Detection Method |
|----------|----------|-----------------|
| `GROOMING` | critical | Sequence analysis on message threads |
| `CYBERBULLYING` | high | Frequency + sentiment per target |
| `SEXTING` | critical | Text + image correlation |

### Confidence Thresholds and Score Combination

The moderation pipeline combines keyword and AI results:

```
keyword_result = keyword_fast_path(text)    # <100ms
ai_result = classify(text)                   # <2s

combined_score = combine(keyword_result, ai_result)

Rules:
1. If keyword says BLOCK with confidence >= 0.90 → REJECT (trust keyword).
2. If AI says BLOCK with confidence >= 0.80 → REJECT (trust AI).
3. If keyword says ALLOW but AI says BLOCK with confidence >= 0.70 →
   AI OVERRIDES keyword → REJECT.
4. If keyword says BLOCK but AI says ALLOW with confidence >= 0.85 →
   AI OVERRIDES keyword → APPROVE (reduces false positives).
5. If both say ALLOW → APPROVE.
6. If neither confident → ESCALATE to human moderator queue.
```

Confidence thresholds are configurable per category and tier. Lower tiers (5-9) use lower thresholds (more aggressive blocking).

### Async Processing

For **pre-publish** content:
- Keyword classifier runs synchronously (fast path, <100ms).
- If keyword result is decisive (BLOCK or high-confidence ALLOW), decision is made immediately.
- If UNCERTAIN, AI classification runs synchronously within the 2s SLA window.

For **post-publish** content:
- Keyword classifier runs synchronously at publish time.
- If keyword says BLOCK, content is taken down immediately (<100ms).
- AI classification runs asynchronously via the background job worker.
- If AI upgrades severity, content is taken down within the SLA window.
- If AI downgrades severity, the keyword block is reversed (content restored).

---

## 5. Image Moderation Pipeline

### Cloudflare Images Webhook Flow

```
Client requests upload
         |
         v
+-------------------------------+
| POST /api/v1/media/upload     |
| src/media/ generates          |
| pre-signed Cloudflare R2 URL  |
| Returns: upload_url, asset_id |
+-------------------------------+
         |
         v
Client uploads to Cloudflare R2
         |
         v
+-------------------------------+
| Cloudflare Images processes:  |
|   - thumbnail (150px)         |
|   - medium (600px)            |
|   - full (1200px)             |
+-------------------------------+
         |
         v
Cloudflare sends webhook
         |
         v
+-------------------------------+
| POST /api/v1/media/webhook    |
| Validates CF webhook signature|
+-------------------------------+
         |
         v
+-------------------------------+
| STEP 1: CSAM CHECK (PhotoDNA) |  <-- ALWAYS runs first
| Hash image against NCMEC DB   |
+-------------------------------+
         |
    +----+----+
    |         |
  CLEAN     MATCH --> [CSAM Flow: Section 7]
    |
    v
+-------------------------------+
| STEP 2: Hive/Sensity          |
| Classification:                |
|   - Nudity detection           |
|   - Violence detection         |
|   - Drug/weapon imagery        |
|   - Hate symbols               |
|   - Age estimation             |
+-------------------------------+
         |
    +----+----+
    v         v
 APPROVE    REJECT
    |         |
    v         v
media_assets  media_assets
.moderation_  .moderation_
status =      status =
'approved'    'rejected'
    |         |
    v         v
CDN serves    CDN blocks
content       (returns 403)
```

### COPPA Consent Gate

Before calling Hive/Sensity (a third-party API), the pipeline checks `check_third_party_consent()` for the `hive_sensity` provider. This follows the existing pattern in `src/risk/engine.py` (Layer 1.5). If consent is missing, image moderation falls back to keyword-only analysis of associated text and a conservative "hold for human review" policy.

### Pre-Signed Upload URL Generation

The `src/media/` module generates Cloudflare R2 pre-signed upload URLs with:
- **Expiry:** 15 minutes.
- **Content-Type restrictions:** `image/jpeg`, `image/png`, `image/webp`, `image/gif` for images.
- **Size limit:** 10MB per image.
- **Metadata:** `asset_id`, `owner_id`, `age_tier` embedded in upload metadata for webhook processing.

### Approval/Rejection Updates

On webhook receipt, `src/media/` updates `media_assets.moderation_status`:
- `pending` (default on upload) -> `approved` or `rejected`.
- If the media is attached to a social post or message, `src/moderation/` is notified via internal interface to update the parent content's `moderation_status`.
- If ANY media attachment on a post is rejected, the entire post is rejected.

---

## 6. Video Moderation Pipeline

### Cloudflare Stream Upload Flow

```
Client requests video upload
         |
         v
+-------------------------------+
| POST /api/v1/media/upload     |
| src/media/ generates          |
| Cloudflare Stream TUS URL     |
| Returns: upload_url, asset_id |
+-------------------------------+
         |
         v
Client uploads via TUS protocol
         |
         v
+-------------------------------+
| Cloudflare Stream processes:  |
|   - Transcode 360p/720p/1080p|
|   - HLS + DASH packaging     |
|   - Thumbnail extraction      |
+-------------------------------+
         |
         v
Cloudflare sends webhook
(status: ready)
         |
         v
+-------------------------------+
| POST /api/v1/media/webhook    |
+-------------------------------+
         |
         v
+-------------------------------+
| FRAME EXTRACTION              |
| Extract key frames only:      |
|   - I-frames (scene changes)  |
|   - 1 frame per 5 seconds     |
|     (whichever is fewer)      |
|   - Max 20 frames per video   |
|   - Thumbnail frame always    |
+-------------------------------+
         |
         v
FOR EACH extracted frame:
         |
         v
+-------------------------------+
| 1. CSAM check (PhotoDNA)      |
| 2. Hive/Sensity classification |
+-------------------------------+
         |
         v
+-------------------------------+
| AGGREGATION:                   |
| IF ANY frame fails ->          |
|   entire video REJECTED        |
| IF ALL frames pass ->          |
|   video APPROVED               |
+-------------------------------+
```

### Cost/Speed Optimization

Key frame extraction, not every frame:
- **I-frames (scene changes):** Most information-dense, most likely to contain problematic content.
- **Sample rate:** 1 frame per 5 seconds for long videos, but never more than 20 frames total.
- **Rationale:** A 60-second video produces ~12 frames. A 5-minute video produces 20 frames (capped). This keeps Hive/Sensity API costs proportional and latency bounded.
- **Max video duration:** 60 seconds for 5-9 tier (disabled), 60 seconds for 10-12 tier, 3 minutes for 13-15 tier.

### Thumbnail Extraction

Before moderation completes, the video thumbnail is extracted by Cloudflare Stream automatically. This thumbnail is:
- Used for preview in pre-publish moderation queue (human moderator sees thumbnail, not full video).
- Subject to the same image moderation pipeline as any other image.
- Stored in `media_assets.variants` JSON field.

---

## 7. CSAM Detection + NCMEC Reporting

**Legal obligation:** Under 18 U.S.C. 2258A, any electronic service provider with knowledge of CSAM must report to NCMEC via CyberTipline. Failure to report is a federal offense.

### PhotoDNA Integration

PhotoDNA (provided free by Microsoft for qualifying services) performs perceptual hash matching against the NCMEC hash database. It runs BEFORE any other moderation step for all image and video content.

```
Image/Video uploaded
         |
         v
+-------------------------------+
| PhotoDNA Hash Match            |
| Compute perceptual hash        |
| Compare against NCMEC DB       |
+-------------------------------+
         |
    +----+----+
    v         v
  CLEAN     MATCH
    |         |
    |    +----v----------------------------+
    |    | 1. BLOCK content immediately    |
    |    |    (never visible to any user)  |
    |    |                                  |
    |    | 2. PRESERVE evidence             |
    |    |    - Original media (encrypted,  |
    |    |      access-restricted storage)  |
    |    |    - PhotoDNA hash               |
    |    |    - Upload metadata (IP, UA,    |
    |    |      timestamp, user agent)      |
    |    |    - Account information          |
    |    |    - DO NOT DELETE (legal hold)   |
    |    |                                  |
    |    | 3. SUBMIT NCMEC CyberTipline    |
    |    |    report via API:               |
    |    |    - Incident details             |
    |    |    - Uploaded file information    |
    |    |    - User/account information     |
    |    |    - IP address + geolocation     |
    |    |                                  |
    |    | 4. SUSPEND account               |
    |    |    - Immediate, no grace period   |
    |    |    - No appeal flow for CSAM      |
    |    |    - All content by user hidden   |
    |    |                                  |
    |    | 5. ALERT admin                   |
    |    |    - PagerDuty/on-call page       |
    |    |    - Admin dashboard flag          |
    |    |    - DO NOT include CSAM content  |
    |    |      in alert (hash only)         |
    |    |                                  |
    |    | 6. LOG for law enforcement       |
    |    |    - Immutable audit trail         |
    |    |    - Separate encrypted log store  |
    |    |    - Retention: indefinite         |
    |    +----------------------------------+
    |
    v
Continue to normal moderation pipeline
```

### Evidence Preservation

CSAM evidence is handled differently from all other moderated content:

| Aspect | Normal Content | CSAM Evidence |
|--------|---------------|---------------|
| Storage after rejection | Soft-deleted, purged after 90 days | Encrypted, retained indefinitely |
| Access | Moderators, admins | Law enforcement liaison only (separate role) |
| Encryption | Standard Fernet (`src/encryption.py`) | Separate CSAM-specific key, hardware-backed if available |
| Audit | `moderation_decisions` table | Separate `csam_evidence_log` table with immutable append-only writes |
| Deletion | Standard data retention policy | NEVER deleted without law enforcement authorization |

### NCMEC CyberTipline API Integration

```python
# Conceptual interface — src/moderation/ncmec.py

async def submit_cybertipline_report(
    incident: CSAMIncident,
) -> NCMECReportResult:
    """Submit a CyberTipline report to NCMEC.

    Required fields per NCMEC API:
    - Incident date/time
    - File information (hash, size, type)
    - Reporter information (ESP details)
    - User information (account, IP, geolocation)
    - Uploaded content reference (secure transfer)

    Returns report ID for tracking.
    Retries on failure with exponential backoff.
    Alerts on-call if submission fails after retries.
    """
```

### Audit Trail

The `csam_evidence_log` table is append-only (no UPDATE or DELETE operations):

```sql
csam_evidence_log:
  id (UUID PK)
  detected_at (timestamptz NOT NULL)
  photodna_hash (text NOT NULL)
  media_asset_id (UUID FK -> media_assets)
  uploader_user_id (UUID FK -> users)
  uploader_ip (inet)
  uploader_user_agent (text)
  ncmec_report_id (text)          -- Returned by CyberTipline API
  ncmec_submission_status (enum: pending/submitted/failed/acknowledged)
  account_suspended_at (timestamptz)
  evidence_storage_key (text)     -- Encrypted reference to preserved content
  admin_notified_at (timestamptz)
  notes (text)                    -- Law enforcement liaison only
  created_at (timestamptz NOT NULL DEFAULT now())
  -- NO updated_at — this table is append-only
```

---

## 8. Moderation Queue Schema

### moderation_queue

```sql
CREATE TABLE moderation_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_type VARCHAR(20) NOT NULL,  -- 'post', 'comment', 'message', 'media'
    content_id UUID NOT NULL,            -- FK to source table (polymorphic)
    pipeline VARCHAR(15) NOT NULL,       -- 'pre_publish', 'post_publish'
    age_tier VARCHAR(10) NOT NULL,       -- 'young', 'preteen', 'teen'
    status VARCHAR(15) NOT NULL DEFAULT 'pending',
        -- 'pending', 'approved', 'rejected', 'escalated', 'appealed'
    risk_scores JSONB NOT NULL DEFAULT '{}',
        -- {
        --   "keyword_score": 0.0,        -- Fast-path keyword confidence
        --   "keyword_categories": [],     -- Categories from keyword match
        --   "ai_score": 0.0,             -- AI classification confidence
        --   "ai_categories": [],          -- Categories from AI classification
        --   "image_score": 0.0,           -- Hive/Sensity score (media only)
        --   "image_categories": [],       -- Image classification categories
        --   "combined_score": 0.0,        -- Final combined score
        --   "combined_categories": [],    -- Final category list
        --   "decision_source": "keyword"  -- Which classifier made the decision
        -- }
    decision_reason TEXT,                -- Human-readable explanation
    author_id UUID NOT NULL,             -- FK to users (content author)
    group_id UUID,                       -- FK to groups (if applicable)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Indexes for latency-critical queries
    CONSTRAINT chk_content_type CHECK (content_type IN ('post', 'comment', 'message', 'media')),
    CONSTRAINT chk_pipeline CHECK (pipeline IN ('pre_publish', 'post_publish')),
    CONSTRAINT chk_age_tier CHECK (age_tier IN ('young', 'preteen', 'teen')),
    CONSTRAINT chk_status CHECK (status IN ('pending', 'approved', 'rejected', 'escalated', 'appealed'))
);

CREATE INDEX ix_moderation_queue_pending
    ON moderation_queue(pipeline, status, created_at)
    WHERE status = 'pending';

CREATE INDEX ix_moderation_queue_content
    ON moderation_queue(content_type, content_id);

CREATE INDEX ix_moderation_queue_author
    ON moderation_queue(author_id, created_at DESC);
```

### moderation_decisions

```sql
CREATE TABLE moderation_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    queue_id UUID NOT NULL REFERENCES moderation_queue(id),
    moderator_id UUID REFERENCES users(id),  -- NULL for automated decisions
    action VARCHAR(20) NOT NULL,
        -- 'approve', 'reject', 'escalate', 'appeal_approve', 'appeal_reject'
    reason TEXT,                              -- Human-readable decision reason
    metadata JSONB DEFAULT '{}',             -- Additional context (classifier version, etc.)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_action CHECK (action IN (
        'approve', 'reject', 'escalate', 'appeal_approve', 'appeal_reject'
    ))
);

CREATE INDEX ix_moderation_decisions_queue
    ON moderation_decisions(queue_id, created_at DESC);
```

### SQLAlchemy Models

These will live in `src/moderation/models.py` and follow the existing pattern with `UUIDMixin`, `TimestampMixin`:

```python
class ModerationQueue(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "moderation_queue"

    content_type = Column(String(20), nullable=False)
    content_id = Column(UUID(as_uuid=True), nullable=False)
    pipeline = Column(String(15), nullable=False)
    age_tier = Column(String(10), nullable=False)
    status = Column(String(15), nullable=False, default="pending")
    risk_scores = Column(JSON, nullable=False, default=dict)
    decision_reason = Column(Text)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"))

class ModerationDecision(UUIDMixin, Base):
    __tablename__ = "moderation_decisions"

    queue_id = Column(UUID(as_uuid=True), ForeignKey("moderation_queue.id"), nullable=False)
    moderator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    action = Column(String(20), nullable=False)
    reason = Column(Text)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

---

## 9. Performance Targets & SLAs

| Metric | Target | Measurement | Alert Threshold |
|--------|--------|-------------|-----------------|
| Keyword check latency | <100ms p99 | Timer in `keyword_fast_path()` | p99 >150ms |
| Pre-publish total latency | <2s p95 | Time from submission to approve/reject | p95 >2s (SLA breach) |
| Post-publish takedown (10-12) | <30s p95 | Time from publish to removal for flagged | p95 >30s |
| Post-publish takedown (13-15) | <60s p95 | Time from publish to removal for flagged | p95 >60s |
| CSAM detection (PhotoDNA) | <5s | Hash match time from upload | >5s |
| Image classification (Hive) | <3s | Hive/Sensity API response time | >5s |
| Video moderation total | <30s for 60s video | Upload webhook to decision | >45s |
| Queue depth | <100 pending items | Count of `status='pending'` AND `created_at > now() - interval '5 min'` | >100 for >5min |
| False positive rate | <5% | Sampled weekly: random 100 rejected items manually reviewed | >5% |
| False negative rate (severe) | <0.1% | Adversarial testing corpus + CSAM synthetic hash tests | >0.1% |
| NCMEC submission success | 100% | All CSAM detections result in successful CyberTipline submission | Any failure |

### Latency Budget (Pre-Publish, 2s SLA)

| Step | Budget | Notes |
|------|--------|-------|
| Age-tier lookup | 5ms | Cached in-memory per session |
| Keyword fast-path | 50ms | In-memory, no I/O |
| AI classification (if needed) | 1500ms | Vertex AI API call |
| Score combination + decision | 5ms | In-memory |
| DB write (queue + status update) | 100ms | Single transaction |
| WebSocket notification | 40ms | Redis pub/sub |
| **Total** | **1700ms** | **300ms headroom** |

---

## 10. Observability

### Structured Logging

Every moderation decision is logged via `structlog` with the following fields:

```python
logger.info(
    "moderation_decision",
    content_type="post",
    content_id="uuid",
    age_tier="preteen",
    pipeline="pre_publish",
    keyword_result="uncertain",
    keyword_latency_ms=45,
    ai_result="reject",
    ai_latency_ms=1200,
    ai_categories=["BULLYING_HARASSMENT"],
    combined_result="reject",
    combined_score=0.87,
    total_latency_ms=1280,
    decision_source="ai",
    queue_id="uuid",
)
```

### Metrics Dashboard (Grafana/Render)

Key panels:
1. **Latency distribution:** p50/p95/p99 for keyword check, AI classification, total pre-publish, total post-publish.
2. **Queue depth over time:** Count of pending items, broken down by pipeline and age tier.
3. **Queue age:** Oldest pending item age. Alert if >30s for pre-publish.
4. **Decision distribution:** Approve/reject/escalate counts over time, broken down by tier and content type.
5. **Classifier agreement:** How often keyword and AI agree vs. disagree (measures classifier quality).
6. **CSAM panel:** Match count (should be near zero), NCMEC submission status, detection latency.

### Alerting Rules

| Condition | Severity | Action |
|-----------|----------|--------|
| Pre-publish p95 >2s | Critical | PagerDuty page on-call |
| Queue depth >100 for >5min | High | PagerDuty alert |
| Any CSAM match | Critical | Immediate page + admin dashboard |
| Failed NCMEC submission | Critical | Immediate page (legal obligation) |
| Post-publish takedown >60s | High | PagerDuty alert |
| False positive rate >5% (weekly) | Medium | Slack notification to moderation team |
| Hive/Sensity API errors >5% | High | PagerDuty alert (image moderation degraded) |
| Vertex AI API errors >10% | Medium | Auto-fallback to keyword-only, Slack notification |

---

## 11. Module Boundaries

### `src/moderation/` Owns

- `moderation_queue` table (all CRUD)
- `moderation_decisions` table (all CRUD)
- `csam_evidence_log` table (append-only)
- Keyword fast-path classifier (word lists, normalization, matching)
- Age-tier routing logic
- Score combination and decision logic
- NCMEC CyberTipline API integration
- Moderation queue management (approve, reject, escalate, appeal)

### Module File Structure

```
src/moderation/
    __init__.py          # Public interface: moderate_content(), get_queue(), approve(), reject()
    router.py            # API endpoints: queue listing, approve/reject, appeal, stats
    service.py           # Core moderation logic, orchestration
    models.py            # ModerationQueue, ModerationDecision, CSAMEvidenceLog
    schemas.py           # Pydantic schemas for API request/response
    keyword_classifier.py # Fast-path keyword matching, word lists, normalization
    word_lists.py        # Per-tier and per-category word lists
    score_combiner.py    # Combines keyword + AI + image scores into final decision
    ncmec.py             # NCMEC CyberTipline API client
    age_tier_router.py   # Determines pre-publish vs post-publish per tier
```

### Cross-Module Communication

| Direction | Interface | Method |
|-----------|-----------|--------|
| `social/` -> `moderation/` | `from src.moderation import moderate_content` | Called when post/comment created |
| `messaging/` -> `moderation/` | `from src.moderation import moderate_content` | Called when message sent |
| `media/` -> `moderation/` | `from src.moderation import moderate_media` | Called on Cloudflare webhook |
| `moderation/` -> `risk/` | `from src.risk import process_event, RISK_CATEGORIES` | AI text classification |
| `moderation/` -> `social/` | `from src.social import update_moderation_status` | Approve/reject content |
| `moderation/` -> `messaging/` | `from src.messaging import update_message_status` | Approve/reject messages |
| `moderation/` -> `media/` | `from src.media import update_media_status` | Approve/reject media |
| `moderation/` -> `alerts/` | `from src.alerts import create_alert` | Parent notifications |

### Social-Specific Risk Models

New social-context classifiers that are NOT part of the existing AI monitoring taxonomy:

- **Grooming detection:** Added as a classifier in `src/risk/` (new `grooming_detector.py`). Called by `src/moderation/` for message thread analysis. Requires message history context (not single-message classification).
- **Cyberbullying detection:** Added as a classifier in `src/risk/` (new `cyberbullying_detector.py`). Uses frequency + sentiment analysis per target user. Requires social graph context.
- **Sexting detection:** Multi-modal — text patterns in `src/risk/`, image nudity detection via Hive in `src/moderation/`. Correlation logic lives in `src/moderation/score_combiner.py`.

These classifiers are registered in `src/risk/taxonomy.py` (extending the category list) but their invocation context (message threads, social graph) is managed by `src/moderation/`.

---

## 12. Testing Strategy

### Unit Tests (`tests/unit/test_moderation.py`)

| Test Area | Count (est.) | Key Cases |
|-----------|:------------:|-----------|
| Keyword matching | 30+ | Exact match, word boundary, no partial match, phrase match |
| Text normalization | 20+ | Unicode, leetspeak, invisible chars, case folding, combined |
| Tier routing | 15+ | Each content type x each tier, missing tier (fallback), feature overrides |
| Score combination | 20+ | Keyword+AI agree, disagree, thresholds, override scenarios |
| Queue state transitions | 15+ | pending->approved, pending->rejected, pending->escalated, appealed |
| NCMEC report building | 5+ | Required fields, IP extraction, retry logic |

### E2E Tests (`tests/e2e/test_moderation.py`)

| Flow | Cases |
|------|-------|
| Pre-publish text (5-9) | Submit -> hold -> keyword check -> approve -> visible |
| Pre-publish text (5-9) | Submit -> hold -> keyword block -> reject -> not visible |
| Post-publish text (13-15) | Submit -> visible -> AI flag -> takedown -> not visible |
| Pre-publish image (10-12) | Upload -> CF webhook -> Hive check -> approve -> visible |
| Appeal flow | Reject -> parent appeal -> re-review -> approve/confirm reject |
| CSAM detection | Upload -> PhotoDNA match -> block + suspend + NCMEC stub |

### Performance Tests

```python
# tests/performance/test_moderation_perf.py
async def test_keyword_check_latency_under_load():
    """1000 concurrent keyword checks should each complete within 100ms."""
    texts = [generate_random_text() for _ in range(1000)]
    start = time.monotonic()
    results = await asyncio.gather(*[keyword_fast_path(t) for t in texts])
    elapsed = time.monotonic() - start
    assert elapsed < 10.0  # 1000 checks in <10s total
    # Also check individual latencies via instrumentation
```

### Adversarial Tests (`tests/unit/test_moderation_adversarial.py`)

| Evasion Technique | Test Case |
|-------------------|-----------|
| Leetspeak | `k1ll y0urs3lf` -> detected as `SELF_HARM` |
| Unicode homoglyphs | `suiсide` (Cyrillic 'с') -> detected |
| Zero-width chars | `su\u200Bicide` -> detected after normalization |
| Whitespace insertion | `s u i c i d e` -> detected with phrase matching |
| Mixed case | `KiLl YoUrSeLf` -> detected after case folding |
| Emoji substitution | Not matched by keyword (flagged by AI classifier) |
| Reversed text | Not matched by keyword (flagged by AI classifier) |

### CSAM Test Policy

- **NEVER use real CSAM material in any test.**
- Use synthetic PhotoDNA hashes (randomly generated, not from NCMEC database).
- Test the hash-matching code path, NCMEC API submission (mocked), account suspension, and evidence preservation with synthetic data.
- PhotoDNA integration testing uses Microsoft's test endpoint with known-clean test images.

---

## Sequence Diagrams

### 1. Pre-Publish Text Flow (5-9 Tier)

```
Child (5-9)        Social App         Moderation         Risk Module        Parent
    |                  |                  |                  |                |
    |  Create post     |                  |                  |                |
    |----------------->|                  |                  |                |
    |                  | moderate_content()|                  |                |
    |                  |----------------->|                  |                |
    |                  |                  | lookup age_tier  |                |
    |                  |                  | tier=young       |                |
    |                  |                  | pipeline=pre_pub |                |
    |                  |                  |                  |                |
    |                  |                  | INSERT           |                |
    |                  |                  | moderation_queue |                |
    |                  |                  | status=pending   |                |
    |                  |                  |                  |                |
    |                  |                  | keyword_fast_path|                |
    |                  |                  | (<100ms)         |                |
    |                  |                  |                  |                |
    |                  |                  |---[if UNCERTAIN]->|                |
    |                  |                  |                  | classify(text) |
    |                  |                  |<--classifications-|                |
    |                  |                  |                  |                |
    |                  |                  | combine_scores() |                |
    |                  |                  | decision=APPROVE |                |
    |                  |                  |                  |                |
    |                  |                  | UPDATE queue     |                |
    |                  |                  | status=approved  |                |
    |                  |                  |                  |                |
    |                  | update_moderation|                  |                |
    |                  | _status=approved |                  |                |
    |                  |<----------------|                  |                |
    |                  |                  |                  |                |
    |  Post visible    |                  |                  |                |
    |<-----------------|                  |                  |                |
    |                  |                  |                  |                |

    [If decision=REJECT]:
    |                  |                  |                  |                |
    |                  |                  | UPDATE queue     |                |
    |                  |                  | status=rejected  |                |
    |                  |                  |                  |                |
    |                  | update_moderation|                  |                |
    |                  | _status=rejected |                  |                |
    |  "Not posted"    |                  |                  |                |
    |<-----------------|                  |                  |                |
    |                  |                  |                  |                |
    |                  |                  | create_alert()   |                |
    |                  |                  |---------------------------------->|
    |                  |                  |                  |   "Blocked     |
    |                  |                  |                  |    post alert" |
```

### 2. Post-Publish Text Flow (13-15 Tier)

```
Teen (13-15)       Social App         Moderation         Risk Module     Background Job
    |                  |                  |                  |                |
    |  Create post     |                  |                  |                |
    |----------------->|                  |                  |                |
    |                  | moderate_content()|                  |                |
    |                  |----------------->|                  |                |
    |                  |                  | lookup age_tier  |                |
    |                  |                  | tier=teen        |                |
    |                  |                  | pipeline=post_pub|                |
    |                  |                  |                  |                |
    |                  |                  | keyword_fast_path|                |
    |                  |                  | result=ALLOW     |                |
    |                  |                  |                  |                |
    |                  |                  | INSERT queue     |                |
    |                  |                  | status=pending   |                |
    |                  |                  |                  |                |
    |                  | publish immediately                 |                |
    |                  | moderation_status                   |                |
    |                  | = 'published'    |                  |                |
    |                  |<----------------|                  |                |
    |                  |                  |                  |                |
    |  Post visible    |                  |                  |                |
    |<-----------------|                  |                  |                |
    |                  |                  |                  |                |
    |                  |                  | enqueue AI check |                |
    |                  |                  |--------------------------------->|
    |                  |                  |                  |                |
    |                  |                  |                  |    (async)     |
    |                  |                  |                  |<---------------|
    |                  |                  |                  | classify(text) |
    |                  |                  |                  |--------------->|
    |                  |                  |                  |                |
    |                  |                  |<--[if AI rejects]--              |
    |                  |                  |                  |                |
    |                  |                  | UPDATE queue     |                |
    |                  |                  | status=rejected  |                |
    |                  |                  |                  |                |
    |                  | update_moderation|                  |                |
    |                  | _status=removed  |                  |                |
    |                  |<----------------|                  |                |
    |                  |                  |                  |                |
    |  Post removed    |                  |                  |                |
    |  from feed       |                  |                  |                |
    |<-----------------|                  |                  |                |
    |                  |                  | create_alert()   |                |
    |                  |                  | -> parent        |                |
```

### 3. Image Upload + Cloudflare + Moderation Flow

```
Child              Mobile App         Media Module       Cloudflare        Moderation
    |                  |                  |                  |                |
    |  Select image    |                  |                  |                |
    |----------------->|                  |                  |                |
    |                  | POST /media/     |                  |                |
    |                  |   upload         |                  |                |
    |                  |----------------->|                  |                |
    |                  |                  | Generate pre-    |                |
    |                  |                  | signed R2 URL    |                |
    |                  |                  | Create media_    |                |
    |                  |                  | assets record    |                |
    |                  |<--- upload_url --|                  |                |
    |                  |                  |                  |                |
    |                  | PUT upload_url   |                  |                |
    |                  |------------------------------------>|                |
    |                  |                  |                  |                |
    |                  |                  |                  | Process image  |
    |                  |                  |                  | (resize, CDN)  |
    |                  |                  |                  |                |
    |                  |                  | Webhook:         |                |
    |                  |                  | image ready      |                |
    |                  |                  |<-----------------|                |
    |                  |                  |                  |                |
    |                  |                  | moderate_media() |                |
    |                  |                  |--------------------------------->|
    |                  |                  |                  |                |
    |                  |                  |                  |  1. PhotoDNA   |
    |                  |                  |                  |     hash check |
    |                  |                  |                  |     (CSAM)     |
    |                  |                  |                  |                |
    |                  |                  |                  |  [if clean]    |
    |                  |                  |                  |                |
    |                  |                  |                  |  2. Hive/      |
    |                  |                  |                  |     Sensity    |
    |                  |                  |                  |     classify   |
    |                  |                  |                  |                |
    |                  |                  |<--- decision ----|                |
    |                  |                  |                  |                |
    |                  |                  | UPDATE media_    |                |
    |                  |                  | assets.          |                |
    |                  |                  | moderation_status|                |
    |                  |                  | = approved       |                |
    |                  |                  |                  |                |
    |  Image visible   |                  |                  |                |
    |<-----------------|                  |                  |                |
```

### 4. CSAM Detection + NCMEC Reporting Flow

```
Uploader           Media Module       Moderation         PhotoDNA          NCMEC       Admin
    |                  |                  |                  |               |            |
    | Upload image     |                  |                  |               |            |
    |----------------->|                  |                  |               |            |
    |                  | CF webhook       |                  |               |            |
    |                  |----------------->|                  |               |            |
    |                  |                  |                  |               |            |
    |                  |                  | hash_check()     |               |            |
    |                  |                  |----------------->|               |            |
    |                  |                  |                  | Compute hash  |            |
    |                  |                  |                  | Match against |            |
    |                  |                  |                  | NCMEC DB      |            |
    |                  |                  |<--- MATCH -------|               |            |
    |                  |                  |                  |               |            |
    |                  |                  | 1. BLOCK content |               |            |
    |                  |                  |    media_assets  |               |            |
    |                  |                  |    .status=      |               |            |
    |                  |                  |    blocked_csam  |               |            |
    |                  |                  |                  |               |            |
    |                  |                  | 2. PRESERVE      |               |            |
    |                  |                  |    evidence      |               |            |
    |                  |                  |    (encrypted    |               |            |
    |                  |                  |     storage)     |               |            |
    |                  |                  |                  |               |            |
    |                  |                  | 3. SUBMIT report |               |            |
    |                  |                  |------------------------------->  |            |
    |                  |                  |                  | CyberTipline  |            |
    |                  |                  |                  | report created|            |
    |                  |                  |<--- report_id ---|               |            |
    |                  |                  |                  |               |            |
    |                  |                  | 4. SUSPEND       |               |            |
    |                  |                  |    account       |               |            |
    |                  |                  |    (immediate)   |               |            |
    |                  |                  |                  |               |            |
    |                  |                  | 5. ALERT admin   |               |            |
    |                  |                  |---------------------------------------------->|
    |                  |                  |                  |               |  PagerDuty |
    |                  |                  |                  |               |  page +    |
    |                  |                  |                  |               |  dashboard |
    |                  |                  |                  |               |            |
    |                  |                  | 6. LOG to        |               |            |
    |                  |                  |    csam_evidence  |               |            |
    |                  |                  |    _log (append  |               |            |
    |                  |                  |     only)        |               |            |
    |                  |                  |                  |               |            |
    | Account          |                  |                  |               |            |
    | suspended        |                  |                  |               |            |
    |<-(kicked out)----|                  |                  |               |            |
```

---

## Open Questions

1. **PhotoDNA access timeline:** Microsoft requires an application process for PhotoDNA. Have we applied? What is the expected approval timeline relative to Phase 1 launch?

2. **NCMEC API credentials:** CyberTipline API access requires ESP registration with NCMEC. Has this process been initiated?

3. **Human moderator staffing:** The pipeline supports escalation to human moderators. What is the staffing plan for Phase 1? Can we rely on automated-only moderation at launch, or do we need human moderators from day one?

4. **Keyword list source:** Where do the initial word lists come from? Options: open-source (e.g., Hive moderation API word lists), commercial (e.g., WebPurify), or curated in-house. Each has different maintenance burden.

5. **Video frame extraction service:** Who extracts key frames from Cloudflare Stream videos? Options: (a) Cloudflare Stream API provides frame access, (b) we download the video and extract locally (CPU-intensive), (c) third-party service. This affects the video moderation latency budget significantly.

6. **Appeal flow design:** The schema supports appeals, but the appeal review process (who reviews, SLA, notification flow) is not fully specified. Should appeals go to: (a) the same automated pipeline with adjusted thresholds, (b) a human moderator, (c) the parent?

7. **Multi-language support:** The keyword lists are English-only initially. The platform supports 6 languages. What is the timeline for non-English keyword lists? AI classification via Vertex AI handles multiple languages natively.

8. **Rate limiting for content creation:** Should there be a per-user content creation rate limit (e.g., max 10 posts/hour) to reduce moderation load and prevent spam? This would be in `src/social/` or `src/moderation/`.

9. **Grooming detection context window:** Grooming detection requires message history analysis (not single-message classification). What is the context window size? Last 50 messages? Last 7 days? The entire conversation? This affects both accuracy and query performance.

10. **CSAM evidence storage location:** Evidence must be retained encrypted and access-restricted. Should this use a separate cloud storage bucket (Cloudflare R2 with separate credentials) or a dedicated encrypted column in PostgreSQL? R2 is better for large media; PostgreSQL is simpler for audit trail integrity.
