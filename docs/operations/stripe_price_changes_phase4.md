# Stripe Price Changes — Phase 4 (Tasks 20, 21)

**Status:** Code deployed; Stripe Dashboard action PENDING USER CONFIRMATION
**Owner:** Platform owner (human action required)
**Date:** 2026-04-17

## Summary

Phase 4 Layer 3 introduces two pricing changes that require Stripe Dashboard actions before production flip:

1. **Task 20 (R-22)** — School tier reduced from $2.99 → $1.99/seat/month
2. **Task 21 (P4-B1)** — New Family+ bundle tier at $19.99/month

Code in `src/billing/plans.py` references new price IDs; these IDs must be created in Stripe Dashboard and the environment variables updated before the price changes take effect in production.

## Task 20: School $1.99/seat + 90-day free pilot

### Required Stripe objects
1. New monthly price for `school_v2` at **$1.99 USD/month per seat**
   - Product: "School Starter" (existing) OR new "School Starter v2"
   - Price ID reference in code: `price_school_v2_monthly`
2. New annual price at **$19.99 USD/year per seat**
   - Price ID reference in code: `price_school_v2_annual`
3. Zero-priced pilot price OR use Stripe trial mechanism (preferred)
   - Product: "School Pilot"
   - 90-day trial with auto-conversion to School Starter v2 at end of pilot

### Rationale
- Undercuts GoGuardian ($4-8/student/year) and Gaggle ($3.75-6/student/year) to drive school adoption
- Sustainable above infrastructure cost
- Free 50-seat / 90-day pilot matches GoGuardian pilot strategy for proof-of-value

## Task 21: Family+ bundle at $19.99/month

### Required Stripe objects
1. New product **"Bhapi Family+"**
2. New monthly price at **$19.99 USD/month**
   - Price ID reference in code: `price_family_plus_monthly`
3. New annual price at **$199.99 USD/year**
   - Price ID reference in code: `price_family_plus_annual`

### Rationale
- Bundles AI monitoring + Social app + device agent + screen time + location + creative + intel network + identity protection + priority support
- Counters Aura's $32/mo bundled value play while offering deeper AI monitoring

## Deployment steps (in order)

1. **Create products and prices in Stripe Dashboard** (or via Stripe CLI):
   ```
   stripe products create --name "School Starter v2" --metadata bhapi_plan_id=school
   stripe prices create --product <id> --unit-amount 199 --currency usd --recurring[interval]=month --metadata bhapi_plan_id=school_monthly
   stripe prices create --product <id> --unit-amount 1999 --currency usd --recurring[interval]=year --metadata bhapi_plan_id=school_annual
   stripe products create --name "Bhapi Family+" --metadata bhapi_plan_id=family_plus
   stripe prices create --product <id> --unit-amount 1999 --currency usd --recurring[interval]=month --metadata bhapi_plan_id=family_plus_monthly
   stripe prices create --product <id> --unit-amount 19999 --currency usd --recurring[interval]=year --metadata bhapi_plan_id=family_plus_annual
   ```
2. **Record price IDs** below (replace placeholders):
   - `STRIPE_PRICE_SCHOOL_V2_MONTHLY=price_...`
   - `STRIPE_PRICE_SCHOOL_V2_ANNUAL=price_...`
   - `STRIPE_PRICE_FAMILY_PLUS_MONTHLY=price_...`
   - `STRIPE_PRICE_FAMILY_PLUS_ANNUAL=price_...`
3. **Set env vars in Render** — update both `core-api` and `jobs` services
4. **Flip existing School subscribers** — customer-support workflow required (migration on next renewal) OR one-off proration
5. **Announce change** — email to existing school admins; blog post for Family+ launch

## Legacy subscription migration

Existing School customers on the `$2.99/seat` price MUST be migrated via Stripe's subscription update flow with proration. Do not leave legacy customers on the old price — this creates billing confusion and support load.

Recommended: run a one-off migration script during a low-activity window, notify customers 14 days in advance.

## Rollback

If any issue surfaces post-launch:
- Keep old Stripe price IDs active (do not archive for 90 days)
- Revert `src/billing/plans.py` to previous pricing via `git revert`
- Set env vars back to legacy price IDs
