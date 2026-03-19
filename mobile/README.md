# Bhapi Mobile

Expo monorepo for the Bhapi mobile apps.

## Apps

- **Bhapi Safety** (`apps/safety`) — Parent monitoring app (com.bhapi.safety)
- **Bhapi Social** (`apps/social`) — Safe social app for children 5-15 (com.bhapi.social)

## Shared Packages

| Package | Description |
|---------|------------|
| `@bhapi/config` | Theme (colors, typography, spacing), constants (age tiers, pricing tiers) |
| `@bhapi/types` | TypeScript types matching backend Pydantic schemas |
| `@bhapi/auth` | JWT token management (SecureStore in Phase 1) |
| `@bhapi/api` | REST + WebSocket API client |
| `@bhapi/i18n` | 6-language translations (EN, PT-BR, ES, FR, DE, IT) |
| `@bhapi/ui` | Shared React Native components (Phase 1) |

## Development

```bash
npm install
npx turbo run test        # Run all tests
npx turbo run typecheck   # Type check all packages
```

## Architecture

See [Bhapi Unified Platform Design Spec](https://github.com/mick-e/bhapi-ai-portal/blob/master/docs/superpowers/specs/2026-03-19-bhapi-unified-platform-design.md) Section 2.2.
