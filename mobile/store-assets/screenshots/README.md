# App Store Screenshots — Bhapi Safety & Bhapi Social

Actual screenshot capture is performed via Maestro E2E flows located in `mobile/maestro/`.
Screenshots must be generated for each device size and language combination before submission.

---

## Required Device Sizes

### iOS (App Store Connect)
| Device | Screen Size | Required |
|--------|-------------|----------|
| iPhone 15 Pro Max | 6.7" (1290 × 2796 px) | Yes — primary |
| iPhone SE (3rd gen) | 4.7" (750 × 1334 px) | Yes |
| iPad Pro 12.9" (6th gen) | 12.9" (2048 × 2732 px) | Yes (if supportsTablet = true) |

### Android (Google Play)
| Device | Screen Size | Required |
|--------|-------------|----------|
| Pixel 8 Pro | 6.7" (1344 × 2992 px) | Yes — primary |
| 7" tablet (generic) | 7" (1200 × 1920 px) | Recommended |

---

## Bhapi Safety App — Key Screens to Capture

### Screen 1: Parent Dashboard
- **Filename prefix:** `safety-01-dashboard`
- **Description:** Overview showing child activity summary, recent alerts, and daily AI usage time.
- **Marketing headline:** "See everything your child does with AI"

### Screen 2: Real-Time Alerts
- **Filename prefix:** `safety-02-alerts`
- **Description:** Alert feed with severity indicators (red/amber/green), platform icons, and one-tap action buttons.
- **Marketing headline:** "Instant alerts for concerning content"

### Screen 3: Member Activity Detail
- **Filename prefix:** `safety-03-activity`
- **Description:** Per-child activity timeline showing AI platforms used, time spent, and risk scores.
- **Marketing headline:** "Full transparency, zero guesswork"

### Screen 4: Content Blocking
- **Filename prefix:** `safety-04-blocking`
- **Description:** Blocking rules screen — scheduled bedtime mode, time budgets, platform toggles.
- **Marketing headline:** "Set limits. Enforce them automatically."

### Screen 5: Family Agreement
- **Filename prefix:** `safety-05-agreement`
- **Description:** Family agreement creation flow with child-friendly language and parent co-signing.
- **Marketing headline:** "Rules your whole family agrees on"

### Screen 6: Weekly Safety Report
- **Filename prefix:** `safety-06-report`
- **Description:** Weekly digest PDF preview with AI usage trends, risk highlights, and recommendations.
- **Marketing headline:** "Weekly reports in plain English"

---

## Bhapi Social App — Key Screens to Capture

### Screen 1: Safe Feed
- **Filename prefix:** `social-01-feed`
- **Description:** Curated social feed with moderated posts, age-appropriate content badges, and friendly UI.
- **Marketing headline:** "A social feed made just for kids"

### Screen 2: Post Creation
- **Filename prefix:** `social-02-create`
- **Description:** Post creation screen with photo/text options, content safety indicator, and fun stickers.
- **Marketing headline:** "Express yourself — safely"

### Screen 3: Profiles & Friends
- **Filename prefix:** `social-03-profile`
- **Description:** Child profile with avatar, post grid, and contact request flow requiring parental approval.
- **Marketing headline:** "Friends approved by parents"

### Screen 4: Direct Messaging
- **Filename prefix:** `social-04-messages`
- **Description:** Chat interface showing moderated conversation with safety badge and reporting button.
- **Marketing headline:** "Chats parents can trust"

### Screen 5: AI Literacy
- **Filename prefix:** `social-05-literacy`
- **Description:** Interactive AI literacy lesson with quiz and achievement badge.
- **Marketing headline:** "Learn how AI works — have fun doing it"

### Screen 6: Safety Status
- **Filename prefix:** `social-06-safety`
- **Description:** Child-facing safety status screen showing their "safety score" and tips in friendly language.
- **Marketing headline:** "Stay safe, stay social"

---

## Language-Specific Screenshots

Screenshots must be localised for each of the 6 supported languages. The app UI renders in the
device locale automatically. Set device language before running Maestro flows.

| Language | Device Locale | Directory suffix |
|----------|---------------|-----------------|
| English (US) | en-US | `en/` |
| French | fr-FR | `fr/` |
| Spanish | es-ES | `es/` |
| German | de-DE | `de/` |
| Portuguese (Brazil) | pt-BR | `pt-br/` |
| Italian | it-IT | `it/` |

### Directory structure expected by EAS Submit
```
store-assets/screenshots/
  safety/
    en/
      safety-01-dashboard-iphone67.png
      safety-02-alerts-iphone67.png
      ...
    fr/
    es/
    de/
    pt-br/
    it/
  social/
    en/
    fr/
    ...
```

---

## Maestro Capture Commands

```bash
# Run Maestro screenshot flow for safety app (English, iPhone 15 Pro Max simulator)
cd mobile
npx maestro test maestro/safety/screenshot-flow.yaml --device "iPhone 15 Pro Max"

# Run for all languages (loop)
for lang in en fr es de pt-br it; do
  DEVICE_LANG=$lang npx maestro test maestro/safety/screenshot-flow.yaml
done
```

> Note: Maestro flows for screenshot capture are planned for Phase 3 — Social Launch.
> Manual screenshots via Xcode Simulator / Android Studio Emulator can be used in the interim.

---

## Store Graphic Specs

| Asset | iOS size | Android size | Notes |
|-------|----------|--------------|-------|
| Feature graphic | N/A | 1024 × 500 px | Google Play banner |
| App icon | 1024 × 1024 px | 512 × 512 px | No alpha on iOS |
| Promotional artwork | 1024 × 1024 px | — | App Store promo tile |
