# NL / PL / SV i18n Translation Package (Phase 4 Task 26)

**Status:** Locale files scaffolded as English clones. **Professional translation PENDING — engage Lokalise, Phrase, or similar.**
**Owner:** Product / Marketing (human action required)
**Date:** 2026-04-19

## Why this matters

Dutch (nl), Polish (pl), and Swedish (sv) open three EU markets where Bhapi's key competitors (Aura, Gaggle, GoGuardian) have limited or no localised presence. Shipping English-only to these markets signals second-class support and depresses conversion.

## Current state

- `portal/messages/nl.json`, `pl.json`, `sv.json` — scaffolded as verbatim clones of `en.json` (2057 lines each)
- `mobile/packages/shared-i18n/locales/` — same (cloned from en.json)
- `portal/src/i18n.ts` — `locales` array extended with `nl`, `pl`, `sv`; `localeLabels` populated with native names
- `portal/src/contexts/LocaleContext.tsx` — load paths registered
- `mobile/packages/shared-i18n/src/index.ts` — load paths registered

**Until professional translations land, users selecting NL/PL/SV will see English content.** The `useTranslations()` hook falls back gracefully (returns the key itself if key is missing) so the app functions correctly; it just looks unlocalised.

## Next steps (process)

1. **Export translation source:** take the canonical `portal/messages/en.json` + `mobile/packages/shared-i18n/locales/en.json` and bundle for the translation vendor (keys are identical between the two; ~2057 lines total)
2. **Engage a translation vendor:**
   - **Lokalise** — good for JSON flat files, supports ICU message format
   - **Phrase** — strong review workflow
   - **Smartling** — enterprise option
3. **Brief the vendor:**
   - Target audience: non-technical parents and school administrators
   - Tone: reassuring, clear, jargon-free (mirror the `CLAUDE.md §6 Content guidance`)
   - Maintain placeholders like `{name}` and HTML tags
   - Glossary: `Bhapi` (brand — do not translate), `Family+` (product name — do not translate), AI platform names (ChatGPT, Gemini, etc. — do not translate)
4. **Review:** require native-speaker reviewer sign-off per locale before merging
5. **QA:** for each locale, smoke-test 5 key pages in local dev and confirm no raw `dashboard.title`-style strings render
6. **Merge:** replace the English-clone files with professionally translated ones

## Smoke tests

- `cd portal && npx vitest run` — should pass (LocaleContext loads new locales without error)
- `cd mobile && npx turbo run test` — mobile i18n loader should pass

## Cost estimate

At typical enterprise rates ($0.10-$0.20 per word):
- en.json has ~8,000 words of UI copy
- 3 languages × ~8,000 words × $0.15/word × 2 (portal + mobile identical keys, should not double-pay if single source) ≈ **$2,400 - $4,800 per round**
- Budget for 2 rounds (initial + post-review revisions): **$5,000 - $10,000 total**

## Why ship scaffolds now

Shipping empty locale registrations + English fallbacks unblocks:
- Marketing to list NL/PL/SV as "supported" on pricing/landing pages (with an asterisk noting English fallback until Q3 2026)
- QA/engineering to test locale-switching paths before the translated content arrives
- Onboarding a translation vendor without a simultaneous code change landing

## Roll-forward plan

When professional translations land:
- Replace the 3 scaffolded JSON files
- No code changes required
- Deploy; users see native copy immediately

## Roll-back

If a translation batch introduces regressions:
- Revert the specific locale JSON file via `git revert`
- All other locales unaffected
