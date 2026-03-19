# bhapi-api Feature Inventory

| Field | Value |
|-------|-------|
| **Repo** | https://github.com/bhapi-inc/bhapi-api |
| **Stack** | Node.js / Express / MongoDB / TypeScript |
| **Language** | TypeScript |
| **Last Push** | 2026-03-16 |
| **Status** | Legacy (pending archive) |

---

## REST Endpoints

### Public API (`/api/v1/`)

| Route Group | File | Purpose |
|-------------|------|---------|
| `/api/v1/auth` | `src/routes/api/v1/auth/index.ts` | Authentication (signup, login, logout, password reset, 2FA verification) |
| `/api/v1/posts` | `src/routes/api/v1/posts/index.ts`, `crud.ts` | Post CRUD (create, read, update, delete, feed listing) |
| `/api/v1/comments` | `src/routes/api/v1/comments/index.ts` | Comment CRUD on posts |
| `/api/v1/followers` | `src/routes/api/v1/followers/index.ts` | Follow/unfollow users, follower lists |
| `/api/v1/messages` | `src/routes/api/v1/messages/index.ts`, `chat.ts` | Direct messages + WebSocket chat |
| `/api/v1/mixed` | `src/routes/api/v1/mixed/index.ts` | Miscellaneous endpoints (search, hashtags, suggestions) |
| `/api/v1/notifications` | `src/routes/api/v1/notifications/index.ts` | Push notification management and listing |
| `/api/v1/options` | `src/routes/api/v1/options/index.ts` | App configuration options |
| `/api/v1/users` | `src/routes/api/v1/users/index.ts`, `crud.ts` | User profile CRUD, account management |

### Back-Office API (`/office/v1/`)

| Route Group | File | Purpose |
|-------------|------|---------|
| `/office/v1/admin` | `src/routes/office/v1/admin/index.ts` | Admin operations (user management, moderation actions) |
| `/office/v1/settings` | `src/routes/office/v1/settings/index.ts`, `initial.ts` | Platform settings, analyzer thresholds, initial setup |

### Other Routes

| Route | File | Purpose |
|-------|------|---------|
| `/download` | `src/routes/download/index.ts` | File/media download endpoints |

---

## Database Models

**File:** `src/models/database.ts`

MongoDB schemas (via Mongoose) covering:

- **User** - Profile, credentials, 2FA settings, role, verification status, birth date, parental consent
- **Post** - Content (text/image/video), author, hashtags, likes, moderation status, toxicity scores
- **Comment** - Post comments with author reference, content, moderation status
- **Message** - Direct messages between users, read status
- **Follower** - Follow relationships between users
- **Notification** - Push notification records (type, recipient, read status)
- **Organization** - Group/org entities that users belong to
- **Settings** - Platform-wide configuration (analyzer thresholds, feature flags)
- **Ticket** - Support ticket records

---

## Third-Party Integrations

### Google Cloud AI Platform

| Service | File | Purpose |
|---------|------|---------|
| **Perspective API** | `src/lib/analyzer.ts` | Text toxicity analysis (scores 0-1 for toxicity, severe toxicity, identity attack, insult, profanity, threat) |
| **Vision API** | `src/lib/media.ts` | Image moderation (safe search detection: adult, violence, racy content) |
| **Video Intelligence API** | `src/lib/media.ts` | Video content moderation (explicit content detection frame-by-frame) |

### Other Integrations

- **Firebase Cloud Messaging (FCM)** - Push notifications (`src/lib/notifications.ts`)
- **SMTP/Email** - Password reset emails (`src/template/reset/user.html`, `src/template/reset/admin.html`)
- **Payment processing** - Payment success/failure templates (`src/template/payments/success.html`, `src/template/payments/failed.html`)

---

## Auth Flow

**File:** `src/routes/api/v1/auth/index.ts`, `src/http/auth.ts`

- Email/password registration with birth date validation
- Login with JWT token issuance
- Two-factor authentication (2FA) via TOTP
  - Enable/disable 2FA flow
  - Verification code validation at login
- Password reset via email link
- Session management with JWT tokens
- Rate limiting on auth endpoints (`src/http/index.ts`)
- HTTP middleware for auth token validation (`src/http/auth.ts`)
- Request helpers and validators (`src/http/help.ts`)

---

## WebSocket Chat

**File:** `src/routes/api/v1/messages/chat.ts`

- Real-time messaging via WebSocket (Socket.io)
- Direct message delivery between authenticated users
- Online/offline status tracking
- Message persistence to MongoDB
- Integration with the REST messages API for message history

---

## Content Moderation Logic

### Analyzer (`src/lib/analyzer.ts`)

- Calls Google Perspective API for text toxicity scoring
- Returns scores across 6 categories: toxicity, severe toxicity, identity attack, insult, profanity, threat
- Configurable thresholds via platform settings
- Posts exceeding thresholds are flagged for moderation review

### Media Moderation (`src/lib/media.ts`)

- Image analysis via Google Vision API safe search
- Video analysis via Google Video Intelligence API
- Detects adult, violent, and racy content
- Returns likelihood scores (VERY_UNLIKELY to VERY_LIKELY)

### Moderator Assignment (`src/lib/moderator.ts`)

- Auto-assigns moderators to flagged content
- Round-robin or load-balanced assignment across available moderators
- Content queue management for moderation review
- Moderation actions: approve, block, escalate

### Mixed Content (`src/lib/mixed.ts`)

- Combined content operations (search, hashtag aggregation)
- Content discovery and suggestion algorithms

### Validation (`src/lib/validation.ts`)

- Input validation for all API endpoints
- Birth date and age verification
- Content length and format validation

### Settings (`src/lib/settings.ts`)

- Platform-wide configuration management
- Toxicity threshold configuration
- Feature flag management

---

## Configuration

**File:** `src/config/index.ts`

- Environment-based configuration (development, staging, production)
- MongoDB connection strings
- Google Cloud credentials
- JWT secret and token expiry
- CORS origins
- Rate limit settings

---

## Type System

| File | Purpose |
|------|---------|
| `src/types/index.ts` | Exported type definitions |
| `src/types/interface.ts` | TypeScript interfaces for all data models and API contracts |

---

## Build & Deploy

| File | Purpose |
|------|---------|
| `package.json` | Dependencies (Express, Mongoose, Socket.io, googleapis, jsonwebtoken, etc.) |
| `tsconfig.json` | TypeScript compiler configuration |
| `nodemon.json` | Development auto-reload configuration |
| `.gcloudignore` | Google Cloud deployment ignore rules |
| `fixtures.json` | Seed data for development/testing |

---

## Open Pull Requests (9 total)

### Snyk Security PRs (7)

Automated dependency vulnerability fix PRs from Snyk bot covering various npm package vulnerabilities.

### Feature PRs (2)

Feature development PRs from contributors (pending review).

---

## Key Architecture Notes

1. **Entry point:** `src/index.ts` - Express app initialization, middleware setup, route mounting, MongoDB connection, Socket.io attachment
2. **Middleware chain:** CORS, rate limiting, JWT auth, request logging
3. **API versioning:** All routes under `/api/v1/` and `/office/v1/`
4. **Email templates:** Handlebars HTML templates for password reset and payment notifications
5. **No test files:** No test directory found in the repository
6. **Security reviews:** `CODE_REVIEW_REPORT.md` and `SECURITY_REVIEW.md` present at root
