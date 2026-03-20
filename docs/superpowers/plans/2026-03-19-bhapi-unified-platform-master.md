# Bhapi Unified Platform — Master Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify Bhapi into a single platform with two mobile apps (Safety + Social), global regulatory compliance, and cross-product AI safety intelligence — positioning as "The only platform where kids socialize safely AND parents monitor AI."

**Architecture:** Expo monorepo (two apps with shared packages) + existing FastAPI monolith (extended with 10 new modules) + separate WebSocket real-time service + Cloudflare R2/Images/Stream for media. PostgreSQL 16 + Redis 7. All social features built as new modules in the existing `src/` structure.

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy async / Alembic / PostgreSQL 16 | Next.js 15 / React 19 / TypeScript / Tailwind | Expo SDK 52+ / React Native 0.76+ / TypeScript / Turborepo | Manifest V3 browser extension | Redis 7 | Stripe | Cloudflare R2/Images/Stream | Render

**Spec:** `docs/superpowers/specs/2026-03-19-bhapi-unified-platform-design.md` (v1.2)

---

## Program Structure

This master plan is organized as **4 phase sub-plans**. Each sub-plan produces working, testable software independently and has explicit dependencies on prior phases.

```
PHASE 0: Emergency Stabilization (Weeks 1-5, Mar 17 — Apr 22)
  Plan: 2026-03-19-phase0-stabilization.md
  Team: 2-3 engineers
  Regulatory deadline: COPPA 2026 (Apr 22) ✅ DONE
  Deliverables: P0-1 through P0-13

PHASE 1: Moat Defense + Safety Foundation (Weeks 6-12, Apr 23 — Jun 8)
  Plan: 2026-04-23-phase1-moat-defense.md ✅ WRITTEN
  Team: 5-7 engineers
  Deliverables: P1-S1→S7, P1-M1→M10, P1-A1→A9, P1-R1→R4, P1-H1→H6
  Tasks: 27 (foundation 3, backend 9, real-time 2, mobile 6, school 5, docs 1, release 1)

PHASE 2: Social Launch + Platform Expansion (Weeks 13-20, Jun 9 — Aug 3)
  Plan: 2026-06-09-phase2-social-launch.md (write at Phase 1 exit)
  Team: 8-10 engineers
  Regulatory deadlines: Ohio AI (Jul 1), EU AI Act (Aug 2)
  Deliverables: P2-S1→S12, P2-M1→M6, P2-C1→C6, P2-E1→E8

PHASE 3: Competitive Parity + Market Launch (Weeks 21-26, Aug 4 — Sep 17)
  Plan: 2026-08-04-phase3-market-launch.md (write at Phase 2 exit)
  Team: 10-13 engineers
  Deliverables: P3-L1→L5, P3-I1→I4, P3-F1→F4, P3-B1→B4
```

### Why Separate Plans

1. **Team composition changes** each phase — plans written later incorporate actual team skills
2. **Codebase evolves** — Phase 2 plan should reference code written in Phase 1, not guesses
3. **Requirements sharpen** — School pilot feedback in Phase 1 informs Phase 2 social app design
4. **Regulatory guidance** — EU AI Act implementing regulations may change between now and August

### Phase Gate Reviews

At each phase exit, before writing the next phase's plan:

1. Run all tests — must meet phase exit test count target
2. Review metrics against exit criteria (spec Section 10)
3. Retrospective: what worked, what didn't, adjust next phase
4. Write next phase's detailed implementation plan using current codebase state

---

## Phase 0 Sub-Plan

See: `docs/superpowers/plans/2026-03-19-phase0-stabilization.md`

This is the only plan written in full detail now. It covers:
- Legacy repo audit and archival (P0-2, P0-3)
- ADR-006 through ADR-010 (P0-4 through P0-7 + P0-3)
- Expo monorepo scaffold (P0-8)
- Australian compliance research (P0-9)
- Moderation architecture design (P0-10)
- Hiring pipeline (P0-11)
- Incident response plan (P0-12)
- Content ownership ToS (P0-13)

---

## Dependency Map

```
Phase 0 (Stabilization)
  │
  ├── ADRs 006-010 ──────────────► Phase 1 (all tracks reference ADRs)
  ├── Expo monorepo scaffold ────► Phase 1 Track B (Safety app)
  ├── Moderation design doc ─────► Phase 1 Track C (AI Safety)
  ├── AU compliance research ────► Phase 1 Track C (P1-A5)
  ├── Incident response plan ────► Phase 1 Track C (T&S ops)
  └── Content ownership ToS ─────► Phase 2 (before Social beta)

Phase 1 (Moat Defense)
  │
  ├── Shared packages ───────────► Phase 2 Track A (Social app uses them)
  ├── Safety app TestFlight ─────► Phase 2 Track B (Safety v2)
  ├── Social backend APIs ───────► Phase 2 Track A (Social app connects)
  ├── Moderation pipeline ───────► Phase 2 Track A (Social content flows through)
  ├── WebSocket service ─────────► Phase 2 Track A (real-time messaging)
  ├── School governance MVP ─────► Phase 2 Track C (Ohio deadline)
  └── FERPA/SDPA readiness ──────► Phase 2 (school deployments)

Phase 2 (Social Launch)
  │
  ├── Social app beta ───────────► Phase 3 Track A (public launch)
  ├── Safety app Store submission ► Phase 3 Track A (public launch)
  ├── Cross-product alerts ──────► Phase 3 Track B (intelligence engine)
  ├── Age-tier enforcement ──────► Phase 3 Track C (creative tools respect tiers)
  └── Anti-abuse measures ───────► Phase 3 (required before public launch)

Phase 3 (Market Launch)
  │
  └── Both apps public ──────────► Post-V1 roadmap
```

---

## Test Count Progression

| Phase Exit | Target | Cumulative |
|-----------|:------:|:----------:|
| Phase 0 | +40 | ~1,887 |
| Phase 1 | +1,105 | ~2,992 |
| Phase 2 | +1,290 | ~4,282 |
| Phase 3 | +830 | ~5,112 |

---

## Weekly Tracking Cadence

Every Monday:
1. `pytest tests/ -v --tb=short` — full backend suite
2. `cd portal && npx vitest run` — frontend suite
3. Count tests vs phase target
4. Review moderation pipeline latency (once live)
5. Update deliverable checkboxes in active phase plan
6. Flag blockers for resolution
