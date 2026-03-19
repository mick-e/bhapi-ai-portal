# ADR-009: Three Age-Tier Permission Model

## Status: Accepted

## Date: 2026-03-19

## Context

The Bhapi Social app (ADR-006) serves children aged 5-15. This age range spans vastly different developmental stages, regulatory requirements, and safety needs:

| Age Range | Developmental Stage | Key Regulations |
|-----------|-------------------|-----------------|
| 5-9 | Early literacy, limited critical thinking, high trust in authority | COPPA (US, <13), GDPR-K (EU, varies by country), Australian Online Safety Act |
| 10-12 | Developing social awareness, peer influence begins, some critical thinking | COPPA (US, <13), GDPR-K (EU, varies), Australian Social Media Minimum Age Bill |
| 13-15 | Adolescent identity formation, desire for autonomy, risk-taking behavior | GDPR-K (some EU countries set 16), Australian Social Media Minimum Age Bill (<16) |

A single permission model for all ages either over-restricts teenagers (driving them to unmonitored platforms) or under-protects young children (exposing them to age-inappropriate interactions).

Additionally, jurisdictional requirements vary. Australia's Social Media Minimum Age Bill restricts users under 16. Some EU countries set GDPR consent age at 16 (Germany, Netherlands) while others set it at 13 (UK, Spain). The permission model must accommodate per-country variations without hardcoding country-specific logic throughout the application.

## Decision

Implement three age tiers with a jurisdiction-aware feature visibility matrix:

### Tier Definitions

| Tier | Age Range | Moderation Mode | Key Restrictions |
|------|-----------|----------------|-----------------|
| **Young** | 5-9 | Pre-publish (all content screened before posting) | No direct messaging (group only), no video, no profile visibility to non-friends, simplified UI |
| **Pre-teen** | 10-12 | Pre-publish (all content screened before posting) | Direct messaging with approved contacts only, no public profile, limited creative tools |
| **Teen** | 13-15 | Post-publish with rapid takedown (<60 seconds) | Full features with monitoring, public profile opt-in (parent approval required), expanded creative tools |

### Data Model

#### `age_tier_configs` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `tier` | ENUM | `young`, `preteen`, `teen` |
| `jurisdiction` | VARCHAR | ISO 3166-1 alpha-2 country code, or `default` |
| `min_age` | INT | Minimum age for this tier in this jurisdiction |
| `max_age` | INT | Maximum age for this tier in this jurisdiction |
| `features` | JSONB | Feature visibility matrix (see below) |
| `moderation_mode` | ENUM | `pre_publish`, `post_publish` |
| `updated_at` | TIMESTAMP | Last modified |

#### Feature Visibility Matrix (JSONB)

```json
{
  "direct_messaging": false,
  "group_messaging": true,
  "video_upload": false,
  "public_profile": false,
  "creative_tools_basic": true,
  "creative_tools_advanced": false,
  "friend_requests": true,
  "feed_posting": true,
  "feed_reactions": true,
  "feed_comments": false,
  "ai_chat": false,
  "location_sharing": false
}
```

#### `feature_overrides` on Group Members

The existing `group_members` table gains a `feature_overrides` JSONB column. Parents can override specific features per child:

```json
{
  "direct_messaging": true,
  "ai_chat": false
}
```

Override rules:
- Parents can **enable** features that the tier disables (e.g., enable direct messaging for a mature 8-year-old).
- Parents can **disable** features that the tier enables (e.g., disable feed posting for a 14-year-old during exam period).
- Parents **cannot** override moderation mode (pre-publish vs post-publish). This is a platform safety decision, not a parental preference.
- Overrides are logged for audit trail.

### Age Transition Handling

A daily background job checks all members' `date_of_birth` against tier boundaries:

1. When a child's age crosses a tier boundary, the job:
   - Sets a `pending_tier_change` flag on the member record.
   - Sends a push notification to the parent: "Alex is turning 10. Their Bhapi experience will update in 7 days. Review the changes."
   - Starts a 7-day grace period.
2. During the grace period, the parent can:
   - Accept the tier change (immediate transition).
   - Review and set feature overrides for the new tier.
3. After 7 days, the tier change applies automatically. Any existing `feature_overrides` incompatible with the new tier are cleared (logged).

### Endpoint Integration

Every social endpoint checks tier permissions via a shared dependency:

```python
async def check_tier_permission(
    feature: str,
    member: GroupMember,
    db: AsyncSession
) -> bool:
    # 1. Get tier config for member's age + jurisdiction
    # 2. Check feature in tier's visibility matrix
    # 3. Check feature_overrides on member
    # 4. Return allowed/denied
```

This is injected as a FastAPI dependency, not scattered as ad-hoc checks.

## Consequences

**Positive:**

- Age-appropriate UX. Young children get a simplified, heavily moderated experience. Teenagers get more autonomy with monitoring.
- Regulatory compliance across jurisdictions. The `jurisdiction` column allows per-country minimum ages without code changes.
- Parental control via overrides. Parents can customize their child's experience within platform safety bounds.
- Graceful age transitions. No jarring sudden changes; parents are notified and can prepare.
- Audit trail. All override changes and tier transitions are logged.

**Negative:**

- Complexity. Every social feature endpoint must check tier permissions. The test matrix is multiplied by 3 tiers times the number of jurisdictions.
- Testing burden. Each feature needs tests for all three tiers, plus override combinations, plus jurisdiction variations. Estimated 3-5x more test cases than a single-tier model.
- UX complexity for parents. The override system, while powerful, adds cognitive load. Parents must understand tiers and features to make informed decisions.

**Risks:**

- Australian exemption denial. If the Australian government does not grant Bhapi an exemption from the Social Media Minimum Age Bill, the platform cannot serve children under 16 in Australia. **Mitigation:** The `jurisdiction` column supports setting `min_age: 16` for `AU`, effectively disabling all tiers below Teen. The fallback is a graceful "not available in your region" message, not a crash.
- Feature override abuse. A parent could enable all features for a 5-year-old, bypassing age-appropriate protections. **Mitigation:** Moderation mode cannot be overridden. Pre-publish screening applies regardless of feature overrides. High-risk features (location sharing) require additional confirmation.
- Tier boundary gaming. A child could lie about their age to get a higher tier. **Mitigation:** Age is set by the parent during member creation and verified via Yoti age verification (ADR-005 / existing integrations module). Children cannot change their own date of birth.

## Alternatives Considered

### Two Tiers (Under-13 / 13+)

- **Pros:** Simpler. Aligns with COPPA's binary under-13/over-13 distinction.
- **Cons:** A 5-year-old and a 12-year-old have nothing in common developmentally. Treating them identically either over-restricts 12-year-olds or under-protects 5-year-olds. Does not account for Australian 16+ requirement.
- **Rejected because:** Too coarse. The 5-9 age group needs fundamentally different protections than 10-12.

### Continuous Age-Based Permissions (Per-Year)

- **Pros:** Maximum granularity. Each age gets exactly the right features.
- **Cons:** 11 different permission sets (ages 5-15) are impractical to configure, test, and explain to parents. UX for parents becomes overwhelming. Regulatory boundaries do not align with per-year granularity.
- **Rejected because:** The testing and UX complexity is not justified. Three tiers capture the meaningful developmental and regulatory boundaries.

## Related ADRs

- [ADR-006](006-two-app-mobile-strategy.md) — Social app uses tier model for child experience
- [ADR-005](005-platform-unification.md) — Unified platform with integrated age verification
