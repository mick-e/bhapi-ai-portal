# Phase 4 Launch Comms Plan

**Status:** Draft. **Marketing / PR coordination PENDING — assign owners before Day -14.**
**Owner:** Founder + Head of Marketing (human action required)
**Launch target:** Q1 2027 (post-SOC 2 Type II issuance)
**Date:** 2026-04-20

## What's shipping in Phase 4

Phase 4 is the "market-leadership" phase. It combines 32 tasks across four layers:

| Area | Headline |
|---|---|
| Compliance | SOC 2 Type II issued, FERPA module live, UK AADC re-review passed, AU eSafety production sign-off |
| Monetisation | Bhapi Family+ bundle ($19.99/mo), School tier reduction to $1.99/seat + free 90-day pilot, identity-protection partnership |
| Platform | Public API GA + 4 SDKs (Python, JS, Swift, Kotlin), intelligence network (cross-customer anonymized threat sharing) |
| Markets | NL / PL / SV added (9 languages total), Apple PermissionKit (iOS 26), Android Digital Wellbeing |
| Hardening | CSP tightened, 138 module-isolation violations fixed, 144 `except Exception:pass` blocks closed |

## Narrative arcs (choose 1-2 for the launch moment)

1. **"The calm safety platform becomes the safety operating system."** Focus on the SOC 2 + FERPA + AADC + AU sign-offs — Bhapi is now the only family AI safety platform with a complete global compliance stack.
2. **"From a parent tool to a developer platform."** Focus on API GA, 4 SDKs, intel network — Bhapi is becoming infrastructure others build on.
3. **"$19.99 for everything — and it includes identity protection."** Focus on Family+ value vs. Aura.

Recommend arc 1 (compliance) for the press cycle and arc 3 (Family+) for the customer-email cycle.

## Audiences + channels

### Existing customers
- **Family subscribers** — product email, in-app banner, dashboard announcement card (reusable `OnboardingTips` component on the dashboard)
- **School admins** — email + personalised outreach from customer success (new SIS integrations, new pricing)
- **API beta partners** — private briefing 1 week before public announcement

### Prospective customers
- Landing page update with Phase 4 headline
- Pricing page with Family+ + School Pilot prominently featured
- `/developers` — new "Public API GA" badge + sample code in 4 languages

### Press / ecosystem
- **Tier 1:** TechCrunch, The Verge, Wired (compliance angle)
- **Tier 2:** K-12 press (THE Journal, EdSurge, EdTech Magazine) for school pricing + FERPA
- **Tier 3:** Regional UK / AU press for AADC + eSafety sign-offs
- **Trade:** ISTE, eSafety Commissioner, Internet Matters (authoritative endorsements)

## Timeline (example; shift ±1 day as needed)

| Day | Action | Owner |
|---|---|---|
| **D-14** | All comms drafts land in review (blog, email, press release, one-pager) | Marketing |
| **D-14** | Sales team enablement call (new tiers, FERPA, compliance stack) | Sales + Marketing |
| **D-10** | Press embargo pitches sent (Tier 1 only) | PR |
| **D-7** | API partner private briefing + changelog | DevRel |
| **D-3** | Customer success outreach to top 20 school accounts | CS |
| **D-1** | Portal banner + in-app announcement staged behind feature flag | Eng |
| **D0** | 08:00 PT — customer email + portal banner goes live | Marketing |
| **D0** | 09:00 PT — blog post + social | Marketing |
| **D0** | 11:00 PT — Tier 1 press embargo lifts | PR |
| **D+1** | Tier 2 press pitches | PR |
| **D+3** | Tier 2 press publishes; partner press quotes | PR |
| **D+7** | Tier 3 press pitches (UK + AU local outlets) | PR |
| **D+14** | Retrospective: MQL volume, sign-up conversion delta, press sentiment | Marketing + Exec |

## Deliverables

### Blog post
`portal/src/app/(dashboard)/blog/phase-4-launch/page.tsx` (or static MDX — match existing blog stack)

Outline:
- Hero: "The family AI safety platform grew up"
- 3 proof points: compliance, developer platform, Family+
- Customer quote (lined up via CS)
- CTAs: start pilot (schools), upgrade to Family+ (existing family users)

### Customer email
Single email, two audience variants:
- Family variant: Family+ pitch + screenshot
- School variant: $1.99/seat + 90-day pilot + FERPA

### Press release
- Single canonical release with quotes from founder + customer
- Distributed via press wire (Business Wire / PR Newswire)
- Localised for UK + AU (timezone + regulatory language)

### One-pager (sales enablement)
- PDF + Notion doc
- Covers: new tiers, compliance certifications, API + SDKs
- Objection handling: "How is this different from Aura?" / "How is this different from GoGuardian?"

### In-product
- Dashboard announcement card (reusable, flag-gated)
- Banner on pricing + landing pages
- Changelog entry at `/changelog`

## KPI targets (measured at D+14)

| KPI | Pre-launch baseline | Launch target | Stretch |
|---|---|---|---|
| Landing-page MQL conversion | 3% | 5% | 7% |
| Pricing-page → checkout CTR | 8% | 12% | 15% |
| Family+ opt-in rate (existing Family subs) | 0% | 10% | 15% |
| School pilot signups | 0 | 5 | 15 |
| API partner signups | 8 | 10+ | 20+ |
| Press mentions (Tier 1) | 0 | 3 | 6 |

Internal metrics dashboard at `/admin/metrics` tracks all of the above.

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Press embargo leaks early | Treat as opportunity — push the announcement up rather than denying |
| SOC 2 report slips past launch day | Keep launch decoupled from SOC 2 — announce "SOC 2 Type II audit in final review" with issuance date when it lands |
| Server load spike on launch (landing page, signup) | Render auto-scales; pre-warm by doing a load test at D-3 |
| Customer confusion over School pricing change | 14-day advance email to existing School customers with transition plan |
| Competitor counter-move | Have response messaging pre-approved by counsel (re: Aura bundle positioning) |

## After-launch

- Continue pushing Tier 2 / Tier 3 press for 2-3 weeks
- Case studies from early pilot schools published at D+45
- First quarterly metrics roll-up at D+90 (Phase 4 close review)
