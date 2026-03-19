# back-office Feature Inventory

| Field | Value |
|-------|-------|
| **Repo** | https://github.com/bhapi-inc/back-office |
| **Stack** | React (CRA) / TypeScript / Redux Toolkit / SCSS |
| **Language** | TypeScript |
| **Last Push** | 2026-03-16 |
| **Status** | Legacy (pending archive) |

---

## Pages (16 total)

### Auth Pages (4)

| Page | File | Purpose |
|------|------|---------|
| Login | `src/pages/auth/login.tsx` | Admin/moderator login |
| Register | `src/pages/auth/register.tsx` | Admin account registration (invite-only) |
| Forgot Password | `src/pages/auth/forgot.tsx` | Password reset request |
| Reset Password | `src/pages/auth/reset.tsx` | Password reset completion |
| Auth Header | `src/pages/auth/header.tsx` | Shared auth page header/branding |

### Dashboard Pages (2)

| Page | File | Purpose |
|------|------|---------|
| Dashboard | `src/pages/dashboard/index.tsx` | Overview metrics (users, posts, reports, tickets) |
| Users Dashboard | `src/pages/dashboard/users.tsx` | User analytics and statistics |

### Content Management Pages (3)

| Page | File | Purpose |
|------|------|---------|
| Published Posts | `src/pages/posts/published.tsx` | View/manage published posts |
| Blocked Posts | `src/pages/posts/blocked.tsx` | Review and manage blocked content |
| Reported Posts | `src/pages/posts/reported.tsx` | Review user-reported content, take action |

### Account Management Pages (2)

| Page | File | Purpose |
|------|------|---------|
| Accounts | `src/pages/accounts/index.tsx` | User account list, search, detail view, suspend/ban |
| Organizations | `src/pages/organizations/index.tsx` | Organization management (create, edit, members) |

### Support Pages (1)

| Page | File | Purpose |
|------|------|---------|
| Tickets | `src/pages/tickets/index.tsx` | Support ticket queue, assignment, resolution |

### Settings Pages (3)

| Page | File | Purpose |
|------|------|---------|
| General Settings | `src/pages/settings/general.tsx` | Platform-wide settings (analyzer thresholds, feature flags) |
| Invitation Settings | `src/pages/settings/invitation.tsx` | Manage invitation codes and access control |
| Email Templates | `src/pages/settings/template.tsx` | Edit email notification templates (rich text editor) |

### Error Page (1)

| Page | File | Purpose |
|------|------|---------|
| Error | `src/pages/error.tsx` | 404 / error fallback page |

---

## RBAC Model (4 Roles)

| Role | Permissions | Scope |
|------|-------------|-------|
| **super-admin** | Full access to all features, settings, and user management | Platform-wide |
| **admin** | User management, content moderation, organization management, ticket handling | Organization-wide |
| **moderator** | Content review (published/blocked/reported), ticket assignment | Content queue |
| **support** | Ticket management, read-only access to accounts and posts | Support queue |

Authorization is enforced in the layout container (`src/layout/container.tsx`).

---

## Post Moderation Workflow

### Post States

```
Created → [Analyzer] → Published (auto-approved)
                     → Flagged → Moderator Review → Published
                                                   → Blocked
User Report → Reported → Moderator Review → Published (dismissed)
                                           → Blocked
```

### Three Content Queues

1. **Published** (`src/pages/posts/published.tsx`) - Live posts, can be blocked or removed
2. **Blocked** (`src/pages/posts/blocked.tsx`) - Posts blocked by moderators or auto-blocked by analyzer, can be restored
3. **Reported** (`src/pages/posts/reported.tsx`) - User-reported posts pending review, can be dismissed or blocked

### Moderation Actions

- **Approve/Publish** - Release content to public feed
- **Block** - Remove from public visibility with reason
- **Dismiss Report** - Mark report as invalid, keep post published
- **Delete** - Permanently remove content
- **Escalate** - Flag for senior moderator/admin review

---

## Account & Organization Management

### Accounts (`src/pages/accounts/`)

- User list with search and filtering
- User detail view (profile, posts, activity)
- Suspend/ban user accounts
- Password reset for users
- Role assignment
- View user moderation history

### Organizations (`src/pages/organizations/`)

- Create and edit organizations
- Manage organization members
- Organization-level settings
- View organization activity/posts

---

## Support Ticket System

**File:** `src/pages/tickets/index.tsx`

- Ticket queue with status filtering (open, in-progress, resolved, closed)
- Ticket assignment to support/moderator staff
- Ticket detail view with conversation thread
- Priority levels
- Resolution tracking
- Linked to user accounts and reported content

---

## Settings

### General Settings (`src/pages/settings/general.tsx`)

- **Analyzer thresholds** - Configure toxicity score thresholds for auto-block vs. flag-for-review
  - Toxicity threshold
  - Severe toxicity threshold
  - Identity attack threshold
  - Insult threshold
  - Profanity threshold
  - Threat threshold
- **Feature flags** - Enable/disable platform features
- **Platform configuration** - General platform settings

### Invitation Settings (`src/pages/settings/invitation.tsx`)

- Generate invitation codes
- View active/used invitation codes
- Revoke invitations
- Invitation limits and expiry

### Email Template Editor (`src/pages/settings/template.tsx`)

- Rich text editor (Lexical-based) for email templates
- Templates for: welcome, password reset, account verification, moderation notifications
- Editor plugins:
  - `AutoLinkPlugin` - Auto-detect and linkify URLs
  - `CodeHighlightPlugin` - Code block syntax highlighting
  - `EditorContentPlugin` - Content state management
  - `ListMaxIndentLevelPlugin` - List indentation limits
  - `ToolbarPlugin` - Formatting toolbar (bold, italic, headers, lists, alignment, etc.)
- Template preview and test send

---

## Components

| Component | File | Purpose |
|-----------|------|---------|
| Button | `src/components/button.tsx` | Primary action button |
| Checkbox | `src/components/checkbox.tsx` | Checkbox input |
| Editor | `src/components/editor/index.tsx` | Rich text editor (Lexical) |
| Modals (Index) | `src/components/modals/index.tsx` | Modal manager |
| Modal: Alert | `src/components/modals/alert.tsx` | Confirmation/alert dialog |
| Modal: Sending | `src/components/modals/sending.tsx` | Loading/sending state overlay |
| Modal: View | `src/components/modals/view.tsx` | Content viewer modal |
| Modal: Account Add | `src/components/modals/account/add.tsx` | Create new admin account |
| Modal: Account Detail | `src/components/modals/account/detail.tsx` | User account detail modal |
| Modal: Org Add | `src/components/modals/organization/add.tsx` | Create organization modal |
| Modal: Post Create | `src/components/modals/post/create.tsx` | Create post on behalf of user |
| Pagination | `src/components/pagination/index.tsx` | Table pagination controls |
| Progress | `src/components/progress.tsx` | Progress bar |
| Search | `src/components/search.tsx` | Search input with debounce |
| Select | `src/components/select.tsx` | Dropdown select |
| Table Bottom | `src/components/table/bottom.tsx` | Table footer with pagination |
| Ticket | `src/components/ticket.tsx` | Support ticket card |

---

## Layout

| File | Purpose |
|------|---------|
| `src/layout/container.tsx` | Main app container with sidebar navigation and RBAC route guards |
| `src/layout/panel.tsx` | Content panel wrapper |

### Known Bug: `container.tsx:48`

**Authorization check at line 48** has a documented bug where the role-based route guard does not properly handle edge cases in role hierarchy. This can allow lower-privilege roles to access restricted pages under certain navigation conditions. Documented here for reference during portal migration -- the new bhapi-ai-portal implements proper RBAC middleware server-side.

---

## Redux Store

### Store Configuration

**File:** `src/redux/store.ts` - Redux Toolkit store setup

### Features (Slices)

| Slice | File | Purpose |
|-------|------|---------|
| Accounts API | `src/redux/features/accounts/api.ts` | RTK Query API for account endpoints |
| Accounts User | `src/redux/features/accounts/user.ts` | Current admin user state |
| Application | `src/redux/features/application.ts` | App-wide state (sidebar, theme, loading) |

### Hooks

**File:** `src/redux/hooks/index.ts` - Typed `useAppDispatch` and `useAppSelector` hooks

---

## Configuration

| File | Purpose |
|------|---------|
| `src/config/application.ts` | App-level configuration (name, version) |
| `src/config/common.ts` | Shared constants |
| `src/config/endpoint.ts` | API endpoint URLs (base URL, versioned paths) |

---

## Helpers

| File | Purpose |
|------|---------|
| `src/helpers/common.ts` | Shared utility functions |
| `src/helpers/http.ts` | HTTP client (Axios instance with auth interceptors) |
| `src/helpers/object.ts` | Object manipulation utilities |
| `src/helpers/storage.ts` | Local storage abstraction (tokens, preferences) |
| `src/helpers/string.ts` | String formatting utilities |

---

## Interfaces

| File | Purpose |
|------|---------|
| `src/interface/common.ts` | Shared TypeScript interfaces |
| `src/interface/http.ts` | HTTP request/response types |
| `src/interface/post.ts` | Post data types |
| `src/interface/user.ts` | User data types |

---

## Routing

**File:** `src/react/router.tsx`

- React Router-based routing
- Route guards based on RBAC roles
- Protected routes redirect to login
- Role-specific route access

### Hooks & Derive

| File | Purpose |
|------|---------|
| `src/react/hooks.tsx` | Custom React hooks |
| `src/react/derive.tsx` | Derived state/computed values |

---

## Lib

| File | Purpose |
|------|---------|
| `src/lib/events.ts` | Event bus for cross-component communication |

---

## Styling

- **SCSS modules** per page (`accounts.scss`, `posts.scss`, `tickets.scss`, `organizations.scss`, `auth.scss`)
- **Global styles:** `src/assets/sass/global.scss`, `common.scss`, `layout.scss`
- **Custom icon font:** IcoMoon (`src/assets/fonts/icomoon/`)
- **Editor theme:** `src/components/editor/themes/toolbar.ts`

---

## Build & Deploy

| File | Purpose |
|------|---------|
| `package.json` | Dependencies and scripts |
| `config-overrides.js` | CRA config overrides (react-app-rewired) |
| `tsconfig.json` | TypeScript configuration |
| `build/` | Pre-built production bundle (committed to repo) |

**Note:** The `build/` directory containing compiled production assets is committed to the repo (unusual practice -- typically gitignored).

---

## Open Pull Requests (3 total)

### Snyk Security PRs (3)

Automated dependency vulnerability fix PRs from Snyk bot covering npm package vulnerabilities in the CRA dependency tree.

---

## Key Architecture Notes

1. **Entry point:** `src/index.tsx` - React app mount with Redux Provider and Router
2. **State management:** Redux Toolkit with RTK Query for API calls
3. **API client:** Axios with auth token interceptors (`src/helpers/http.ts`)
4. **Editor:** Lexical (Meta's rich text editor) with 5 custom plugins
5. **Build tool:** Create React App with config-overrides (react-app-rewired)
6. **No test files:** Only `src/setupTests.ts` present (no actual test files)
7. **Security review:** `CODE_REVIEW_REPORT.md` present at root
8. **Pre-built assets:** `build/` directory committed to repo with production bundle
