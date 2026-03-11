# Bhapi AI Portal — Family Safety Features Implementation Plan

**Version:** 2.0.0
**Created:** 2026-03-10
**Updated:** 2026-03-11
**Status:** Complete
**Total Features:** 16 (F1–F16) — All implemented
**Actual Effort:** ~45 developer-days across 7 parallel sprints

---

## Progress Tracker

| # | Feature | Priority | Sprint | Est. Days | Status | Backend | Frontend | Tests |
|---|---------|----------|--------|-----------|--------|---------|----------|-------|
| F1 | AI Conversation Summaries | P0 | 4 | 5 | Complete | `src/capture/summarizer.py`, `summary_models.py` | Member detail page | 21 unit + E2E |
| F2 | Emotional Dependency Detection | P0 | 2 | 4 | Complete | `src/risk/dependency.py` | DependencyGauge + sparkline | 11 unit + E2E |
| F3 | COPPA 2026 Compliance Dashboard | P0 | 1 | 3 | Complete | `src/compliance/coppa.py` | Compliance page | E2E |
| F4 | AI Academic Integrity Dashboard | P1 | 6 | 4 | Complete | Risk classifier patterns | `portal/academic/page.tsx` | E2E |
| F5 | Family AI Agreement | P1 | 5 | 4 | Complete | `src/groups/agreement.py` | Settings + member detail | E2E |
| F6 | Smart AI Screen Time | P1 | 3 | 4 | Complete | `src/blocking/time_budget.py` | TimerGauge + budget editor | E2E |
| F7 | Deepfake & Synthetic Content Protection | P1 | 6 | 3 | Complete | `src/risk/deepfake_detector.py` | Guidance hook + UI | E2E |
| F8 | Family Safety Weekly Report | P2 | 5 | 3 | Complete | `src/reporting/family_report.py` | Reports page | E2E |
| F9 | Panic Button / Instant Report | P2 | 3 | 3 | Complete | `src/alerts/panic.py` | Alerts page + child dashboard | E2E |
| F10 | AI Platform Safety Ratings | P2 | 1 | 2 | Complete | `src/risk/platform_safety.py` | Safety ratings cards | E2E |
| F11 | Sibling Privacy Controls | P2 | 7 | 4 | Complete | `src/groups/member_visibility.py` | Privacy tab in settings | E2E |
| F12 | Multi-Device Correlation | P3 | 7 | 2 | Complete | `src/analytics/device_correlation.py` | Device breakdown on member detail | E2E |
| F13 | Bedtime Mode | P3 | 3 | 1 | Complete | `src/blocking/time_budget.py` | Bedtime schedule editor | E2E |
| F14 | AI Usage Allowance Rewards | P3 | 7 | 3 | Complete | `src/groups/rewards.py` | Rewards section on member detail | E2E |
| F15 | Emergency Contact Integration | P3 | 5 | 2 | Complete | `src/groups/emergency_contacts.py` | Emergency Contacts tab | E2E |
| F16 | Family Onboarding Wizard | P3 | 1 | 2 | Complete | Existing onboarding flow | Child dashboard (`my-dashboard/page.tsx`) | E2E |

**Legend:** ~~Not Started~~ | ~~In Progress~~ | **Complete** | ~~Blocked~~

---

## Sprint Schedule

| Sprint | Week | Features | Focus | Days |
|--------|------|----------|-------|------|
| 1 | 1 | F3 + F10 + F16 | Regulatory + onboarding | 7 |
| 2 | 2 | F2 | Emotional safety (highest child risk) | 4 |
| 3 | 3 | F6 + F9 + F13 | Parental controls | 8 |
| 4 | 4 | F1 | Content visibility (top differentiator) | 5 |
| 5 | 5 | F5 + F8 + F15 | Engagement + retention | 9 |
| 6 | 6 | F4 + F7 | School market + compliance | 7 |
| 7 | 7 | F11 + F12 + F14 | Polish + family UX | 9 |

---

## Feature Specifications

---

### F1: AI Conversation Summaries for Parents

**Why:** 42% of parents say their #1 concern is AI chatbots not reporting troubling behavior. Bhapi captures metadata but parents can't see what their child discussed. This is the #1 differentiator vs. Bark.

**Prerequisites:** Enhanced monitoring consent must be granted for the member. Content capture (`POST /api/v1/capture/content`) must be active.

#### Backend

**New files:**
- `src/capture/summarizer.py` — LLM-powered conversation summarization service

```python
# Key functions
async def summarize_conversation(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    content: str,
    platform: str,
) -> ConversationSummary:
    """Generate a parent-friendly summary of an AI conversation.

    Uses Claude API (or configurable LLM) to produce:
    - Topics discussed (list of 3-5 tags)
    - Emotional tone (neutral/positive/concerned/distressed)
    - Risk flags (any content matching risk taxonomy)
    - Key quotes (up to 3 notable excerpts)
    - Parent action needed (yes/no with reason)
    """

async def generate_daily_summaries(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    date: date,
) -> list[ConversationSummary]:
    """Batch-summarize all conversations for a member on a given date."""

async def get_member_summaries(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResult[ConversationSummary]:
    """List summaries with pagination."""
```

- `src/capture/summary_models.py` — SQLAlchemy model

```python
class ConversationSummary(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "conversation_summaries"

    group_id: UUID          # FK groups
    member_id: UUID         # FK group_members
    capture_event_id: UUID  # FK capture_events (nullable, links to source)
    platform: str           # chatgpt, claude, etc.
    date: date              # date of conversation
    topics: list[str]       # JSON array of topic tags
    emotional_tone: str     # neutral, positive, concerned, distressed
    risk_flags: list[str]   # JSON array of risk categories detected
    key_quotes: list[str]   # JSON array of notable excerpts (max 3)
    action_needed: bool     # parent should review
    action_reason: str      # why action needed (nullable)
    summary_text: str       # 2-3 sentence plain-English summary
    detail_level: str       # full, moderate, minimal (based on age)
    llm_model: str          # which model generated summary
    content_hash: str       # SHA-256 of source content (dedup)
```

**Modified files:**
- `src/capture/router.py` — add endpoints:
  - `GET /api/v1/capture/summaries` — list summaries (group_id, member_id, date range)
  - `GET /api/v1/capture/summaries/{summary_id}` — single summary detail
  - `POST /api/v1/capture/summarize` — trigger manual summarization for an event
- `src/capture/schemas.py` — add `ConversationSummaryResponse`, `SummaryListResponse`
- `src/jobs/runner.py` — register `daily_summarization` job (runs daily, summarizes previous day's enhanced captures)
- `src/config.py` — add `SUMMARY_LLM_PROVIDER` (anthropic/openai), `SUMMARY_LLM_MODEL`, `SUMMARY_LLM_API_KEY`

**Age-based detail levels:**
- Under 10: `full` — complete summary with all quotes and context
- 11-13: `moderate` — summary + risk flags, fewer quotes
- 14-16: `minimal` — risk flags only, no quotes unless critical severity
- 17+: `minimal` — risk flags only

**Privacy design:**
- Raw content never stored in summary table — only processed output
- Source content remains encrypted in capture_events with TTL
- Summaries inherit TTL from group settings (default 90 days)
- LLM API call uses no-retention mode where supported

#### Frontend

**New files:**
- `portal/src/app/(dashboard)/activity/summaries/page.tsx` — summary feed page
  - Date picker (defaults to today)
  - Member filter dropdown
  - Summary cards: platform icon + topics + tone badge + risk flag pills + summary text
  - "Action needed" cards highlighted with amber border
  - Expand to see key quotes
- `portal/src/hooks/use-summaries.ts` — React Query hook for summary API

**Modified files:**
- `portal/src/app/(dashboard)/members/detail/page.tsx` — add "Recent Summaries" section (last 5)
- `portal/src/app/(dashboard)/dashboard/page.tsx` — add "Today's Highlights" card (action-needed summaries)
- `portal/src/types/index.ts` — add `ConversationSummary` interface

#### New Alembic migration
- `alembic/versions/010_conversation_summaries.py` — creates `conversation_summaries` table

#### Email template
- Daily "Conversation Digest" email (top 3 notable interactions, sent at 8am)

#### Tests
- Unit: `tests/unit/test_summarizer.py` — mock LLM responses, test age-level detail
- E2E: `tests/e2e/test_summaries.py` — CRUD endpoints, pagination, date filtering
- Security: verify summaries respect group isolation, require auth

---

### F2: Emotional Dependency Detection & Scoring

**Why:** A 14-year-old died by suicide after forming an intense attachment to Character.AI. FTC launched formal inquiry Sept 2025. No competitor does this comprehensively.

**Prerequisites:** Extension monitors Character.ai, Replika, Pi.ai (already implemented). Emotional dependency keyword patterns exist in classifier (basic set).

#### Backend

**New files:**
- `src/risk/emotional_dependency.py` — dedicated emotional dependency analysis service

```python
# Dependency score components (0-100, higher = more dependent)
@dataclass
class DependencyScore:
    score: int                    # 0-100 composite
    session_duration_score: int   # 0-25 based on avg session length
    frequency_score: int          # 0-25 based on daily interaction count
    attachment_language_score: int # 0-25 based on keyword pattern matches
    time_pattern_score: int       # 0-25 based on late-night/early-morning usage
    trend: str                    # improving, stable, worsening
    risk_factors: list[str]       # human-readable risk factor descriptions
    platform_breakdown: dict      # per-platform scores
    recommendation: str           # parent guidance text

async def calculate_dependency_score(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    days: int = 30,
) -> DependencyScore:
    """Calculate emotional dependency score for a member.

    Components:
    1. Session duration (0-25): avg session >45min on companion platforms
       - <15min: 0, 15-30min: 8, 30-45min: 15, 45-60min: 20, >60min: 25
    2. Frequency (0-25): daily interaction count on companion platforms
       - 0-1/day: 0, 2-3/day: 8, 4-5/day: 15, 6-8/day: 20, >8/day: 25
    3. Attachment language (0-25): keyword pattern match rate in content
       - Based on risk events with EMOTIONAL_DEPENDENCY category
    4. Time pattern (0-25): % of sessions after 10pm or before 6am
       - <10%: 0, 10-25%: 8, 25-50%: 15, 50-75%: 20, >75%: 25
    """

async def get_dependency_history(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    days: int = 90,
) -> list[DependencyDataPoint]:
    """Weekly dependency scores over time."""

COMPANION_PLATFORMS = {"characterai", "replika", "pi"}

# Escalation triggers
ALERT_THRESHOLD = 60       # Create medium alert
CRITICAL_THRESHOLD = 80    # Create high alert + SMS
TRIGGERS = [
    "score_crossed_threshold",      # Score exceeds 60 or 80
    "session_duration_doubled",     # Avg session 2x baseline
    "late_night_surge",             # >50% sessions after 10pm (new pattern)
    "emotional_goodbye",            # "goodbye" + emotional language detected
    "frequency_spike",              # 3x daily interaction baseline
]
```

**Modified files:**
- `src/risk/classifier.py` — expand emotional dependency patterns:
  ```python
  # New patterns to add (medium severity, 0.80 confidence)
  r"\b(you'?re\s+the\s+only\s+one\s+who\s+(?:gets|understands)\s+me)\b"
  r"\b(i\s+(?:think\s+about|dream\s+about)\s+you\s+all\s+the\s+time)\b"
  r"\b((?:my\s+)?(?:parents|friends)\s+don'?t\s+understand\s+me\s+like\s+you)\b"
  r"\b(i\s+(?:feel|am)\s+(?:so\s+)?(?:alone|lonely)\s+without\s+you)\b"
  r"\b(promise\s+(?:me\s+)?you'?ll\s+(?:never|always))\b"
  r"\b(i\s+(?:told|tell)\s+you\s+(?:things|stuff)\s+i'?ve?\s+never\s+told\s+anyone)\b"
  ```
- `src/risk/router.py` — add endpoints:
  - `GET /api/v1/risk/dependency-score` — member dependency score
  - `GET /api/v1/risk/dependency-score/history` — weekly score history
- `src/risk/schemas.py` — add `DependencyScoreResponse`, `DependencyHistoryResponse`
- `src/jobs/runner.py` — register `dependency_check` job (daily, calculates scores, creates alerts on threshold)
- `src/alerts/service.py` — add dependency-specific alert creation with parent guidance text

#### Frontend

**Modified files:**
- `portal/src/app/(dashboard)/members/detail/page.tsx` — add "Emotional Dependency" section:
  - Circular gauge (green 0-40, amber 41-60, red 61-100)
  - Risk factor pills (e.g., "Late-night usage", "High frequency")
  - Trend arrow (improving/stable/worsening)
  - "Learn More" expandable with parent guidance text
  - Weekly history sparkline chart
- `portal/src/app/(dashboard)/risks/page.tsx` — add dependency score summary card at top
- `portal/src/app/(dashboard)/dashboard/page.tsx` — add dependency alert in "Action Needed" section
- `portal/src/hooks/use-dependency.ts` — React Query hook
- `portal/src/types/index.ts` — add `DependencyScore` interface

#### Email template
- "Emotional Dependency Alert" — sent when score crosses threshold, includes:
  - Score and trend
  - Risk factors in plain language
  - "How to talk to your child about AI relationships" guidance
  - Link to Common Sense Media resources

#### Tests
- Unit: `tests/unit/test_emotional_dependency.py` — score calculation with various inputs, threshold triggers
- E2E: `tests/e2e/test_dependency.py` — endpoint auth, score response schema, history pagination
- Security: verify score isolation per group

---

### F3: COPPA 2026 Compliance Dashboard

**Why:** FTC finalized COPPA Rule updates Jan 2025. Compliance deadline is **April 22, 2026** — one month away. Expanded "personal information" definition, requires formal infosec programs.

**Prerequisites:** ConsentRecord model exists. COPPA consent verification exists. Audit logging exists.

#### Backend

**New files:**
- `src/compliance/coppa_dashboard.py` — COPPA compliance assessment service

```python
@dataclass
class COPPAChecklistItem:
    id: str                    # e.g., "consent_all_members"
    label: str                 # "All members have verified parental consent"
    description: str           # detailed explanation
    status: str                # complete, incomplete, warning, not_applicable
    evidence: str | None       # what proves compliance (e.g., "5/5 members consented")
    action_url: str | None     # link to fix (e.g., "/consent")
    regulation_ref: str        # "16 CFR § 312.5(a)"

@dataclass
class COPPAComplianceReport:
    group_id: UUID
    score: int                 # 0-100 percentage complete
    status: str                # compliant, partial, non_compliant
    checklist: list[COPPAChecklistItem]
    generated_at: datetime
    next_review_due: date      # 90-day review cycle
    export_available: bool

async def assess_coppa_compliance(db, group_id) -> COPPAComplianceReport:
    """Auto-assess COPPA compliance for a group.

    Checklist items:
    1. Parental consent recorded for all members under 13 ✓/✗
    2. Consent method is FTC-approved (5 methods) ✓/✗
    3. PII detection enabled in risk config ✓/✗
    4. Content encryption enabled ✓/✗
    5. Data retention policy configured (<= 1 year) ✓/✗
    6. Data deletion requests honored within 72 hours ✓/✗
    7. Privacy policy accessible (link configured) ✓/✗
    8. No marketing consent collected from children ✓/✗
    9. Third-party data sharing audit complete ✓/✗
    10. Infosec program documentation uploaded ✓/✗
    11. Biometric data handling policy (new 2026 requirement) ✓/✗
    12. Annual compliance review completed ✓/✗
    """

async def export_coppa_evidence(db, group_id) -> bytes:
    """Generate PDF evidence package for FTC Safe Harbor submission.

    Includes:
    - Compliance checklist with timestamps
    - All consent records with method and evidence
    - Audit log of data access and deletions
    - Privacy policy text
    - Infosec program summary
    """
```

**Modified files:**
- `src/compliance/router.py` — add endpoints:
  - `GET /api/v1/compliance/coppa/checklist` — auto-assessed checklist
  - `GET /api/v1/compliance/coppa/export` — PDF evidence package download
  - `POST /api/v1/compliance/coppa/review` — mark annual review complete
- `src/compliance/schemas.py` — add response schemas
- `src/jobs/runner.py` — register `coppa_reminder` job (daily, alerts if review overdue or compliance gaps)

#### Frontend

**New files:**
- `portal/src/app/(dashboard)/compliance/coppa/page.tsx` — COPPA dashboard page
  - Compliance score gauge (0-100%) with status badge (Compliant/Partial/Non-Compliant)
  - Checklist with status icons (green check, red X, amber warning)
  - Each item expandable with description + regulation reference + fix action button
  - "Export Evidence" button (downloads PDF)
  - "Mark Review Complete" button
  - Next review due date display
  - April 2026 deadline countdown banner
- `portal/src/hooks/use-coppa.ts` — React Query hook

**Modified files:**
- `portal/src/app/(dashboard)/compliance/page.tsx` — add COPPA card with score + link to dashboard
- `portal/src/app/(dashboard)/dashboard/page.tsx` — add compliance status widget if score < 100%

#### Tests
- Unit: `tests/unit/test_coppa_dashboard.py` — checklist assessment with various states
- E2E: `tests/e2e/test_coppa_compliance.py` — endpoint auth, checklist response, PDF export

---

### F4: AI Academic Integrity Dashboard

**Why:** 89% of students use AI for homework. 100% of principals are concerned. Schools need visibility, not policing.

#### Backend

**New files:**
- `src/analytics/academic.py` — academic usage analysis service

```python
STUDY_HOUR_DEFAULTS = {
    "weekday": {"start": "15:00", "end": "21:00"},  # 3pm-9pm
    "weekend": {"start": "09:00", "end": "21:00"},  # 9am-9pm
}

# Prompt intent classification
LEARNING_PATTERNS = [
    r"\b(explain|how\s+does|what\s+is|why\s+does|teach\s+me|help\s+me\s+understand)\b",
    r"\b(what\s+are\s+the\s+(?:steps|differences|similarities))\b",
    r"\b(can\s+you\s+(?:explain|clarify|break\s+down))\b",
]

DOING_PATTERNS = [
    r"\b(write\s+(?:my|an?|the)\s+(?:essay|paper|report|paragraph))\b",
    r"\b(solve\s+(?:this|these|my)\s+(?:problem|equation|homework))\b",
    r"\b(do\s+my\s+(?:homework|assignment|project))\b",
    r"\b(answer\s+(?:these|this|my)\s+(?:question|quiz))\b",
    r"\b(complete\s+(?:this|my)\s+(?:worksheet|assignment))\b",
    r"\b(give\s+me\s+(?:the\s+)?answer)\b",
]

@dataclass
class AcademicReport:
    member_id: UUID
    period_start: date
    period_end: date
    total_ai_sessions: int
    study_hour_sessions: int       # sessions during configured study hours
    learning_count: int            # classified as learning-oriented
    doing_count: int               # classified as task-completion
    unclassified_count: int        # couldn't determine intent
    learning_ratio: float          # learning / (learning + doing)
    top_subjects: list[str]        # extracted topic tags
    daily_breakdown: list[dict]    # per-day: {date, learning, doing, total}
    recommendation: str            # parent/teacher guidance

async def generate_academic_report(
    db, group_id, member_id, start_date, end_date
) -> AcademicReport

async def classify_prompt_intent(content: str) -> str:
    """Classify prompt as 'learning', 'doing', or 'unclassified'."""
```

**Modified files:**
- `src/analytics/router.py` — add `GET /api/v1/analytics/academic` endpoint
- `src/analytics/schemas.py` — add `AcademicReportResponse`
- `src/capture/service.py` — tag events during study hours with metadata
- `src/groups/models.py` — add `study_hours` to group settings JSON schema

#### Frontend

**New files:**
- `portal/src/app/(dashboard)/analytics/academic/page.tsx` — academic integrity page
  - Period selector (this week / last week / this month)
  - Member selector
  - Learning vs. Doing pie chart
  - Daily breakdown bar chart (stacked: learning green, doing amber)
  - Top subjects word cloud or tag list
  - Study hours configuration form
  - Weekly trend with learning ratio line chart

**Modified files:**
- `portal/src/app/(dashboard)/members/detail/page.tsx` — add "Academic AI Usage" card
- `portal/src/hooks/use-analytics.ts` — add academic report query

#### Tests
- Unit: `tests/unit/test_academic.py` — intent classification accuracy, study hours logic
- E2E: `tests/e2e/test_academic.py` — endpoint auth, report generation

---

### F5: Family AI Agreement / Digital Contract

**Why:** 49% of parents have NEVER spoken to their child about AI. Experts recommend "gradual exposure" with clear rules.

#### Backend

**New files:**
- `src/groups/agreement.py` — agreement management service

```python
class FamilyAgreement(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "family_agreements"

    group_id: UUID             # FK groups
    title: str                 # "Smith Family AI Agreement"
    template_id: str           # age-band template used as base
    rules: list[dict]          # JSON: [{category, rule_text, enabled}]
    signed_by_parent: UUID     # FK users (parent who created)
    signed_by_parent_at: datetime
    signed_by_members: list[dict]  # JSON: [{member_id, name, signed_at}]
    active: bool
    review_due: date           # next quarterly review
    last_reviewed: date | None

AGREEMENT_TEMPLATES = {
    "ages_7_10": {
        "title": "Family AI Rules (Ages 7-10)",
        "rules": [
            {"category": "platforms", "text": "I will only use AI tools my parent has approved"},
            {"category": "time", "text": "I will use AI for no more than 30 minutes per day"},
            {"category": "content", "text": "I will not share my name, school, or address with AI"},
            {"category": "safety", "text": "I will tell my parent if AI says something that scares or confuses me"},
            {"category": "honesty", "text": "I will not use AI to do my homework for me"},
            {"category": "supervision", "text": "I will use AI in a shared family space"},
        ],
    },
    "ages_11_13": { ... },
    "ages_14_16": { ... },
    "ages_17_plus": { ... },
}
```

**Modified files:**
- `src/groups/router.py` — add agreement CRUD endpoints:
  - `GET /api/v1/groups/{group_id}/agreement` — get active agreement
  - `POST /api/v1/groups/{group_id}/agreement` — create from template
  - `PATCH /api/v1/groups/{group_id}/agreement` — update rules
  - `POST /api/v1/groups/{group_id}/agreement/sign` — member signs
  - `GET /api/v1/groups/agreement-templates` — list templates
- `src/jobs/runner.py` — register `agreement_review_reminder` (weekly, checks if review_due passed)

#### Frontend

**New files:**
- `portal/src/app/(dashboard)/family/agreement/page.tsx` — agreement page
  - Template selector cards (by age band)
  - Rule editor: toggle individual rules, add custom rules
  - Digital signature section: parent signs first, then each child
  - Active agreement display with rule checklist
  - "Violations" section linking rule breaks to risk events
  - Quarterly review prompt with "Review Now" button

#### New Alembic migration
- `alembic/versions/011_family_agreements.py`

#### Tests
- E2E: `tests/e2e/test_agreement.py` — CRUD, signing flow, template selection

---

### F6: Smart AI Screen Time

**Why:** Google Family Link and Apple Screen Time don't understand AI-specific usage. Parents want to limit AI time specifically.

#### Backend

**New files:**
- `src/blocking/time_budget.py` — AI time budget management

```python
class TimeBudget(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "time_budgets"

    group_id: UUID
    member_id: UUID
    weekday_minutes: int       # daily budget Mon-Fri (default 60)
    weekend_minutes: int       # daily budget Sat-Sun (default 120)
    reset_hour: int            # hour to reset daily counter (default 0 = midnight)
    timezone: str              # member's timezone (default UTC)
    enabled: bool
    warn_at_percent: int       # show warning at this % (default 75)

class TimeBudgetUsage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "time_budget_usage"

    group_id: UUID
    member_id: UUID
    date: date
    minutes_used: int          # accumulated from session durations
    budget_minutes: int        # snapshot of budget for this day
    exceeded: bool
    exceeded_at: datetime | None

async def check_time_budget(db, group_id, member_id) -> TimeBudgetStatus:
    """Returns: {minutes_used, budget_minutes, remaining, exceeded, warn}"""

async def record_session_time(db, group_id, member_id, minutes: int) -> None:
    """Called by capture service on session_end events."""

async def enforce_time_budgets(db) -> dict:
    """Job: create auto-block rules for exceeded budgets, remove expired ones."""
```

**Modified files:**
- `src/blocking/router.py` — add time budget endpoints:
  - `GET /api/v1/blocking/time-budget/{member_id}` — get budget + usage
  - `PUT /api/v1/blocking/time-budget/{member_id}` — set budget
  - `GET /api/v1/blocking/time-budget/{member_id}/history` — daily usage history
- `src/capture/service.py` — on `session_end` event, calculate duration and call `record_session_time()`
- `src/jobs/runner.py` — register `time_budget_enforce` job (every_5m)
- Extension: `extension/src/background/service-worker.ts` — track session start time, calculate duration on end

#### Frontend

**Modified files:**
- `portal/src/app/(dashboard)/members/detail/page.tsx` — add "AI Screen Time" card:
  - Circular progress (minutes used / budget)
  - Weekday/weekend budget configurator
  - 7-day usage bar chart
  - Toggle to enable/disable
- `portal/src/app/(dashboard)/blocking/page.tsx` — add "Screen Time" tab with all members' budgets
- Extension: `extension/src/popup/popup.html` — add time remaining display

#### New Alembic migration
- `alembic/versions/012_time_budgets.py`

#### Tests
- Unit: `tests/unit/test_time_budget.py` — budget calculation, timezone handling, weekend detection
- E2E: `tests/e2e/test_time_budget.py` — CRUD, enforcement, history

---

### F7: Deepfake & Synthetic Content Protection

**Why:** AI-generated CSAM reports increased 600%+ in H1 2025. TAKE IT DOWN Act (May 2025) criminalizes nonconsensual deepfakes.

**Prerequisites:** `src/risk/deepfake_detector.py` exists with Hive/Sensity provider abstraction. `DEEPFAKE_CONTENT` category in taxonomy.

#### Backend

**Modified files:**
- `src/risk/classifier.py` — expand deepfake/nudify patterns:
  ```python
  # New patterns (high severity, 0.90 confidence)
  r"\b(remove\s+(?:her|his|their)\s+clothes)\b"
  r"\b(make\s+(?:a\s+)?nude\s+(?:photo|image|picture))\b"
  r"\b(clone\s+(?:my|her|his)\s+voice)\b"
  r"\b(voice\s+sample|voice\s+recording\s+for\s+(?:ai|cloning))\b"
  r"\b(face\s+(?:on|onto)\s+(?:a\s+)?(?:body|video|photo))\b"
  r"\b(undress\s+(?:ai|app|tool|website))\b"
  ```
- `src/risk/engine.py` — enhance Layer 1.5 (deepfake detection):
  - Extract media URLs from AI responses when content captured
  - Submit to Hive/Sensity API for analysis
  - Create risk event if deepfake confidence > threshold (default 0.7)
- `src/risk/deepfake_detector.py` — add `detect_voice_cloning_risk()` for voice-related patterns
- `src/alerts/service.py` — deepfake alert template with:
  - "What is a deepfake?" explanation
  - NCMEC CyberTipline link (report.cybertip.org)
  - FBI IC3 link
  - TAKE IT DOWN Act removal process steps

#### Frontend

**Modified files:**
- `portal/src/app/(dashboard)/risks/page.tsx` — add DEEPFAKE_CONTENT category display:
  - Red badge with shield icon
  - Guidance card when deepfake risk detected
  - One-click "Report to NCMEC" button (opens external link)
- `portal/src/app/(dashboard)/members/detail/page.tsx` — deepfake risk indicator if any events

#### Tests
- Unit: `tests/unit/test_deepfake_enhanced.py` — new patterns, voice cloning detection
- E2E: `tests/e2e/test_deepfake.py` — full pipeline with mock Hive responses

---

### F8: Family Safety Weekly Report

**Why:** Current digests are alert-focused (what went wrong). Parents want a positive summary showing overall safety posture.

#### Backend

**New files:**
- `src/reporting/family_report.py` — weekly family safety report generator

```python
async def generate_family_weekly_report(
    db: AsyncSession,
    group_id: UUID,
) -> FamilyWeeklyReport:
    """Generate comprehensive weekly report.

    Sections:
    1. Family safety score (group average + trend)
    2. Per-member cards:
       - Safety score + trend arrow
       - AI platforms used (with time spent if F6 enabled)
       - Risk events (count by severity)
       - Top conversation topics (if F1 enabled)
       - Comparison to previous week
    3. Highlights:
       - Best safety score improvement
       - Longest streak without high-severity events
       - Literacy modules completed
    4. Action items:
       - Unresolved alerts
       - Pending approvals
       - Overdue agreement review
    5. Coming up:
       - Trial expiry warning
       - COPPA review due
    """

async def send_family_weekly_report(db: AsyncSession, group_id: UUID) -> bool:
    """Generate PDF + send via email to all parents in group."""
```

**Modified files:**
- `src/jobs/runner.py` — register `family_weekly_report` job (weekly, Sunday 8am)
- `src/reporting/generators.py` — add `FamilyWeeklyPDFGenerator` class
- `src/email/service.py` — add weekly report email template

#### Frontend

**Modified files:**
- `portal/src/app/(dashboard)/reports/page.tsx` — add "Weekly Family Report" section:
  - Preview of latest report
  - "Send Now" button for on-demand generation
  - Configuration: recipient emails, send day/time, sections to include
- `portal/src/app/(dashboard)/settings/page.tsx` — add weekly report toggle in notifications

#### Tests
- Unit: `tests/unit/test_family_report.py` — report generation, section assembly
- E2E: `tests/e2e/test_family_report.py` — endpoint, PDF generation

---

### F9: Panic Button / Instant Report

**Why:** Children need a way to tell their parent immediately when something disturbs them.

#### Backend

**New files:**
- `src/alerts/panic.py` — panic report service

```python
class PanicReport(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "panic_reports"

    group_id: UUID
    member_id: UUID
    category: str          # scary_content, weird_request, bad_ai_response, other
    message: str | None    # optional child's description (500 chars max)
    platform: str | None   # which AI platform
    session_id: str | None # link to capture session
    parent_response: str | None  # parent's response text
    parent_responded_at: datetime | None
    resolved: bool

CATEGORY_LABELS = {
    "scary_content": "Something scared me",
    "weird_request": "Someone asked me something weird",
    "bad_ai_response": "AI said something bad",
    "other": "Something else happened",
}

PARENT_QUICK_RESPONSES = [
    "I'm coming to talk to you right now",
    "Thank you for telling me. Let's discuss after school",
    "I'm glad you told me. You did the right thing",
    "Are you okay? I'll call you in a minute",
]

async def create_panic_report(db, data: PanicReportCreate) -> PanicReport:
    """Create report + critical alert + SMS to all parents in group."""

async def respond_to_panic(db, report_id, user_id, response) -> PanicReport:
    """Parent responds to child's report."""
```

**Modified files:**
- `src/alerts/router.py` — add endpoints:
  - `POST /api/v1/alerts/panic` — child submits panic report
  - `GET /api/v1/alerts/panic` — list panic reports
  - `POST /api/v1/alerts/panic/{report_id}/respond` — parent responds
- `src/sms/service.py` — panic alert SMS template (bypasses digest, immediate send)

#### Frontend (Extension)

**Modified files:**
- `extension/src/popup/popup.html` — add prominent red "I Need Help" button
- `extension/src/popup/popup.ts` — panic button handler:
  - Click → category selector (4 options)
  - Optional message textarea
  - Submit → POST to `/api/v1/alerts/panic`
  - Confirmation: "Your parent has been notified"

#### Frontend (Portal)

**Modified files:**
- `portal/src/app/(dashboard)/alerts/page.tsx` — panic reports section with:
  - Highlighted card (red border, bell icon)
  - Quick-response buttons
  - Custom response textarea
  - Resolution toggle
- `portal/src/app/(dashboard)/dashboard/page.tsx` — panic alert banner (highest priority)

#### New Alembic migration
- `alembic/versions/013_panic_reports.py`

#### Tests
- E2E: `tests/e2e/test_panic.py` — report creation, SMS trigger, parent response

---

### F10: AI Platform Safety Ratings for Parents

**Why:** Parents don't know which platforms are safer. Existing vendor risk is technical; parents need simple grades.

#### Backend

**New files:**
- `src/billing/platform_safety.py` — parent-facing platform safety ratings

```python
PLATFORM_SAFETY_PROFILES = {
    "chatgpt": {
        "name": "ChatGPT (OpenAI)",
        "overall_grade": "B+",
        "min_age_recommended": 13,
        "has_parental_controls": True,
        "has_content_filters": True,
        "data_retention_days": 30,
        "coppa_compliant": True,
        "known_incidents": 1,
        "strengths": ["Strong content filters", "Family plan available", "Usage dashboard"],
        "concerns": ["Can generate creative fiction with mature themes", "No real-time parent monitoring"],
        "last_updated": "2026-03-01",
    },
    "claude": { ... },   # Grade: A
    "gemini": { ... },   # Grade: B+
    "copilot": { ... },  # Grade: B
    "grok": { ... },     # Grade: B-
    "characterai": { ... }, # Grade: C- (emotional dependency risk)
    "replika": { ... },  # Grade: D (romantic mode, emotional dependency)
    "pi": { ... },       # Grade: B
}

async def get_platform_safety_ratings() -> list[PlatformSafetyRating]:
    """All platforms with parent-friendly safety info."""

async def get_age_recommendations(age: int) -> list[PlatformRecommendation]:
    """Platforms recommended/not recommended for a specific age."""
```

**Modified files:**
- `src/billing/router.py` — add endpoints:
  - `GET /api/v1/billing/platform-safety` — all ratings (public, no auth)
  - `GET /api/v1/billing/platform-safety/{platform}` — single platform detail
  - `GET /api/v1/billing/platform-safety/recommend?age=12` — age-appropriate recommendations

#### Frontend

**New files:**
- `portal/src/app/(dashboard)/safety-ratings/page.tsx` — platform safety ratings page
  - Grid of platform cards with grade badge (color-coded A-F)
  - Age filter: "Show recommendations for age ___"
  - Each card: platform name, grade, min age, content filter status, strengths/concerns
  - Expandable detail with full profile
  - "Recommended" / "Not Recommended" / "Use with caution" labels per age

**Modified files:**
- `portal/src/app/(dashboard)/dashboard/page.tsx` — add "Platform Safety" quick card

#### Tests
- Unit: `tests/unit/test_platform_safety.py` — rating data, age recommendations
- E2E: `tests/e2e/test_platform_safety.py` — public endpoint, age filtering

---

### F11: Sibling Privacy Controls

**Why:** In families with multiple children, the 16-year-old's data shouldn't be visible to younger siblings. Divorced parents may need separate access.

#### Backend

**New files:**
- `src/groups/privacy.py` — member visibility and scoping service

```python
class MemberVisibility(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "member_visibility"

    group_id: UUID
    member_id: UUID        # the child
    visible_to: UUID       # the parent who can see this child's data
    # If no MemberVisibility rows exist for a member, all parents can see (default)

class ChildSelfView(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "child_self_views"

    group_id: UUID
    member_id: UUID
    enabled: bool          # parent has enabled self-view for this child
    sections: list[str]    # JSON: which sections visible ["safety_score", "time_usage", "literacy"]
    # Never includes: other siblings' data, raw risk events, parent alerts

async def check_member_visibility(db, group_id, user_id, member_id) -> bool:
    """Check if user_id is allowed to see member_id's data."""

async def get_child_dashboard(db, group_id, member_id) -> ChildDashboard:
    """Age-appropriate dashboard data for a child viewing their own data."""
```

**Modified files:**
- `src/dependencies.py` or middleware — add visibility check to all member-scoped endpoints
- `src/groups/router.py` — add visibility management endpoints:
  - `PUT /api/v1/groups/{group_id}/members/{member_id}/visibility` — set which parents can see
  - `GET /api/v1/groups/{group_id}/members/{member_id}/self-view` — child self-view config
  - `PUT /api/v1/groups/{group_id}/members/{member_id}/self-view` — enable/configure self-view
- `src/portal/router.py` — add child dashboard endpoint:
  - `GET /api/v1/portal/child-dashboard` — filtered data for child's own view

#### Frontend

**New files:**
- `portal/src/app/(dashboard)/my-dashboard/page.tsx` — child self-view page
  - Safety score (own only)
  - AI time used today
  - Literacy progress + next module suggestion
  - "I Need Help" panic button
  - No access to other siblings' data, no admin controls

**Modified files:**
- `portal/src/app/(dashboard)/settings/page.tsx` — add "Privacy" tab:
  - Per-child visibility toggles (which parent sees which child)
  - Self-view enable/disable per child
  - Section selector for self-view

#### New Alembic migration
- `alembic/versions/014_member_visibility.py`

#### Tests
- E2E: `tests/e2e/test_privacy.py` — visibility enforcement, child self-view scoping
- Security: `tests/security/test_sibling_privacy.py` — cross-member data isolation

---

### F12: Multi-Device Correlation

**Why:** Same child uses AI on phone, laptop, and school Chromebook. Total daily AI time needs aggregation.

#### Backend

**Modified files:**
- `src/capture/service.py` — add device correlation:
  ```python
  async def get_member_session_summary(db, group_id, member_id, date) -> SessionSummary:
      """Aggregate sessions across all registered devices.

      Returns: total_minutes, session_count, device_breakdown, platform_breakdown
      """
  ```
- `src/capture/models.py` — add `device_id` field to `CaptureEvent` (FK to `device_registrations`)
- `src/capture/router.py` — add `GET /api/v1/capture/devices/{member_id}/summary` endpoint

#### Frontend

**Modified files:**
- `portal/src/app/(dashboard)/members/detail/page.tsx` — add "Devices" section:
  - List of registered devices with last-seen timestamp
  - Per-device usage breakdown (bar chart)
  - Total daily aggregation across devices

#### Tests
- E2E: `tests/e2e/test_device_correlation.py` — multi-device session aggregation

---

### F13: Bedtime Mode

**Why:** Simple UX for time-of-day blocking during sleep hours. Uses existing auto-block infrastructure.

#### Backend

**Modified files:**
- `src/blocking/service.py` — add bedtime mode helpers:
  ```python
  async def set_bedtime_mode(db, group_id, member_id, start_hour, end_hour, timezone) -> AutoBlockRule:
      """Create/update time_of_day auto-block rule with bedtime UX.

      Adds 15-min wind-down warning before block activates.
      """
  ```
- `src/blocking/router.py` — add:
  - `PUT /api/v1/blocking/bedtime/{member_id}` — set bedtime hours
  - `GET /api/v1/blocking/bedtime/{member_id}` — get current bedtime config

#### Frontend

**Modified files:**
- `portal/src/app/(dashboard)/members/detail/page.tsx` — add "Bedtime Mode" toggle card:
  - Enable/disable toggle
  - Start/end time selectors (hour dropdowns)
  - Timezone selector
  - "Active now" indicator with countdown to end
- Extension: show "Bedtime — AI tools are offline until [time]" overlay

#### Tests
- E2E: `tests/e2e/test_bedtime.py` — bedtime rule creation, wind-down behavior

---

### F14: AI Usage Allowance Rewards

**Why:** Positive reinforcement. Children earn extra AI time by maintaining good safety scores or completing literacy modules.

#### Backend

**New files:**
- `src/groups/rewards.py` — reward/gamification service

```python
class Reward(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "rewards"

    group_id: UUID
    member_id: UUID
    reward_type: str       # extra_time, badge, achievement
    trigger: str           # literacy_complete, safety_streak, agreement_compliance
    value: int             # minutes of extra time, or badge tier
    earned_at: datetime
    expires_at: datetime | None
    redeemed: bool

REWARD_TRIGGERS = {
    "literacy_module_complete": {"type": "extra_time", "value": 15},      # +15 min
    "safety_score_above_80": {"type": "extra_time", "value": 30},         # +30 min per week
    "week_no_high_risk": {"type": "badge", "value": 1},                   # "Safety Star" badge
    "agreement_compliance_week": {"type": "extra_time", "value": 20},     # +20 min
}
```

**Modified files:**
- `src/blocking/time_budget.py` — factor in earned rewards when calculating remaining budget
- `src/jobs/runner.py` — register `reward_check` job (daily, awards earned rewards)

#### Frontend

**Modified files:**
- Child self-view page (F11) — add "My Rewards" section with earned badges and extra time
- `portal/src/app/(dashboard)/members/detail/page.tsx` — add rewards history

#### New Alembic migration
- `alembic/versions/015_rewards.py`

#### Tests
- E2E: `tests/e2e/test_rewards.py` — trigger earning, budget integration

---

### F15: Emergency Contact Integration

**Why:** Critical-severity events (self-harm, CSAM) may warrant notifying a trusted contact beyond the parent.

#### Backend

**New files:**
- `src/groups/emergency_contacts.py` — emergency contact management

```python
class EmergencyContact(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "emergency_contacts"

    group_id: UUID
    name: str
    relationship: str      # grandparent, school_counselor, trusted_adult
    phone: str | None
    email: str | None
    notify_on: list[str]   # JSON: ["critical", "self_harm", "csam_adjacent"]
    consent_given: bool    # contact has agreed to receive notifications
    consent_given_at: datetime | None

async def notify_emergency_contacts(db, group_id, alert: Alert) -> int:
    """Send notification to emergency contacts if alert matches their notify_on criteria.
    Returns count of contacts notified."""
```

**Modified files:**
- `src/alerts/service.py` — on critical alert creation, call `notify_emergency_contacts()`
- `src/groups/router.py` — add emergency contact CRUD endpoints
- `src/sms/service.py` — emergency contact SMS template

#### Frontend

**Modified files:**
- `portal/src/app/(dashboard)/settings/page.tsx` — add "Emergency Contacts" section:
  - Add/edit/remove contacts
  - Configure notification triggers
  - Consent tracking display

#### New Alembic migration
- `alembic/versions/016_emergency_contacts.py`

#### Tests
- E2E: `tests/e2e/test_emergency_contacts.py` — CRUD, notification triggering

---

### F16: Family Onboarding Wizard

**Why:** Reduce time-to-value from ~15min to ~5min for new families.

**Prerequisites:** OnboardingWizard component exists in portal (referenced in dashboard). Group creation flow exists.

#### Backend

**Modified files:**
- `src/groups/router.py` — add onboarding completion endpoint:
  - `POST /api/v1/groups/{group_id}/onboarding-complete` — marks onboarding done, sets defaults

#### Frontend

**Modified files:**
- `portal/src/app/(dashboard)/dashboard/page.tsx` — enhance existing onboarding:
  - Step 1: Welcome + create group (exists)
  - Step 2: Add children — name, age, relationship (new)
  - Step 3: Set age-appropriate safety defaults (strict/moderate/permissive) (new)
  - Step 4: Install extension — browser selection + setup code generation (new, integrates extension page)
  - Step 5: Choose family agreement template (new, links to F5)
  - Step 6: First literacy module for child (new, links to literacy)
  - Progress bar at top showing steps 1-6
  - "Skip for now" on optional steps (5, 6)
  - Completion celebration screen with "Go to Dashboard" CTA

#### Tests
- Frontend: `portal/src/tests/onboarding.test.tsx` — wizard step progression, skip logic

---

## Database Migrations Summary

| Migration | Feature | Tables |
|-----------|---------|--------|
| 010 | F1 | `conversation_summaries` |
| 011 | F5 | `family_agreements` |
| 012 | F6 | `time_budgets`, `time_budget_usage` |
| 013 | F9 | `panic_reports` |
| 014 | F11 | `member_visibility`, `child_self_views` |
| 015 | F14 | `rewards` |
| 016 | F15 | `emergency_contacts` |

**Features without new tables:** F2, F3, F4, F7, F8, F10, F12, F13, F16 (use existing models or JSON config)

---

## New Environment Variables

| Variable | Feature | Required |
|----------|---------|----------|
| `SUMMARY_LLM_PROVIDER` | F1 | For conversation summaries |
| `SUMMARY_LLM_MODEL` | F1 | For conversation summaries |
| `SUMMARY_LLM_API_KEY` | F1 | For conversation summaries |

All other features use existing infrastructure (no new env vars).

---

## New Scheduled Jobs

| Job | Schedule | Feature | Description |
|-----|----------|---------|-------------|
| `daily_summarization` | daily | F1 | Summarize previous day's conversations |
| `dependency_check` | daily | F2 | Calculate dependency scores, create alerts |
| `coppa_reminder` | daily | F3 | Check COPPA compliance gaps, alert if overdue |
| `time_budget_enforce` | every_5m | F6 | Enforce exceeded time budgets |
| `family_weekly_report` | weekly | F8 | Generate and email weekly family report |
| `agreement_review_reminder` | weekly | F5 | Remind if quarterly review overdue |
| `reward_check` | daily | F14 | Award earned rewards |

---

## Test Estimates

| Feature | Unit | E2E | Security | Frontend | Total |
|---------|------|-----|----------|----------|-------|
| F1 | 8 | 10 | 3 | 5 | 26 |
| F2 | 10 | 8 | 2 | 3 | 23 |
| F3 | 6 | 8 | 2 | 4 | 20 |
| F4 | 8 | 6 | 1 | 4 | 19 |
| F5 | 5 | 8 | 2 | 5 | 20 |
| F6 | 10 | 8 | 2 | 4 | 24 |
| F7 | 6 | 5 | 2 | 2 | 15 |
| F8 | 5 | 5 | 1 | 3 | 14 |
| F9 | 4 | 6 | 2 | 4 | 16 |
| F10 | 4 | 5 | 1 | 3 | 13 |
| F11 | 6 | 8 | 5 | 4 | 23 |
| F12 | 4 | 5 | 1 | 2 | 12 |
| F13 | 3 | 4 | 1 | 2 | 10 |
| F14 | 5 | 6 | 1 | 3 | 15 |
| F15 | 4 | 6 | 2 | 2 | 14 |
| F16 | 2 | 3 | 0 | 4 | 9 |
| **Total** | **90** | **101** | **28** | **54** | **273** |

Projected test count after all features: **1053 + 273 = ~1,326 tests**

---

## Verification Checklist (per feature)

1. `pytest tests/ -v` — all backend tests pass
2. `cd portal && npx vitest run` — all frontend tests pass
3. `cd portal && npx tsc --noEmit` — no TypeScript errors
4. Manual smoke test via portal
5. Production security test pass
6. Update this document's progress tracker
7. Update `CLAUDE.md` if routes/modules/test counts change
8. Update `docs/bhapi-post-mvp-roadmap.md` if applicable

---

## Architecture Notes

### Patterns to Follow
- **Backend module structure:** `router.py` + `service.py` + `models.py` + `schemas.py`
- **Frontend page pattern:** `"use client"` + `useQuery` hooks + loading/error/empty states + Card layout
- **API client pattern:** Add to `portal/src/lib/api-client.ts` with typed helpers
- **Test pattern:** Happy path + auth (403) + validation (422) + edge cases
- **Job pattern:** Register in `src/jobs/runner.py` with `register_job()`
- **No raw HTTPException** — use `BhapiException` subclasses
- **No cross-module imports** — use public interfaces in `__init__.py`
- **Async everywhere** — SQLAlchemy async, httpx
- **Email TLD** — `.test` rejected in validation; always use `.com` in tests
- **Test fixture** — use `test_session` (not `async_db`)

### Key Constraints
- **No `next/image`** — use plain `<img>` tags (static export)
- **No dynamic `[id]` routes** — use query parameters
- **No server components** — `"use client"` everywhere
- **Family member cap** — MAX_FAMILY_MEMBERS = 5
- **Content encryption** — always via `src/encryption.py`
- **BudgetThreshold** — uses `type` field (not `threshold_type`)
- **Capture events** — paginated `{items, total, page, page_size, total_pages}`
