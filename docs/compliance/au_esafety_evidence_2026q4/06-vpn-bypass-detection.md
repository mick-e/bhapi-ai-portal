# 06 — VPN / Bypass Detection (s63F "reasonable steps")

**Requirement:** Social Media Minimum Age Act requires "reasonable steps" to detect and prevent circumvention of age restrictions. eSafety guidance suggests VPN/proxy detection + alt-URL detection are reasonable measures.

## Code references

- `src/blocking/vpn_detection.py` — server-side receiver + auto-block escalation (Phase 4 Task 23)
- `extension/src/content/bypass_detector.ts` — client-side probes
- `alembic/versions/059_bypass_attempts.py` — audit table

## Detection techniques

1. **WebRTC IP leak** — dual-IP heuristic via STUN probe
2. **Alt-AI URL patterns** — regex match against known mirror/proxy domains
3. **Incognito/private window detection** — storage quota heuristic
4. **Extension tampering** — SHA-256 manifest hash check

## Escalation

- Each attempt: high-severity alert to group admins
- 3+ attempts in 60-minute rolling window: auto-block for 24h via `vpn_bypass_auto` rule
- Idempotent: repeated triggering doesn't pile on additional rules

## Tests

- `tests/e2e/test_vpn_detection.py` (9 passing tests)
- single attempt logs without auto-block
- 3 attempts trigger auto-block
- idempotency, coalescing, old-attempt exclusion all tested

## Counsel review items

- Is this detection stack sufficient as "reasonable steps" under s63F? (eSafety guidance accepts VPN detection as one of several reasonable measures)
- Do we need to block access entirely on detection, or is 24h cool-off acceptable?
- Extension is optional — what about users on mobile without the extension? (Device agent + mobile app enforcement are in roadmap)
