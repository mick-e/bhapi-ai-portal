# bhapi-mobile Feature Inventory

| Field | Value |
|-------|-------|
| **Repo** | https://github.com/bhapi-inc/bhapi-mobile |
| **Stack** | React Native 0.64.2 / JavaScript / Redux / React Navigation |
| **Language** | JavaScript |
| **Last Push** | 2026-03-17 |
| **Platforms** | iOS (Swift bridge) + Android (Java) |
| **Status** | Legacy (pending archive) |

---

## Screens (43 total)

### Auth Screens (10)

| Screen | Path | Purpose |
|--------|------|---------|
| Login | `src/Screens/Auth/Login/` | Email/password login |
| Signup (Form) | `src/Screens/Auth/Signup/Form/` | Registration form (email, password, username) |
| Signup (Birth) | `src/Screens/Auth/Signup/Birth/` | Birth date entry and age verification |
| Signup (Parent) | `src/Screens/Auth/Signup/Parent/` | Parental consent flow for minors |
| Signup (Bio) | `src/Screens/Auth/Signup/Bio/` | Profile bio setup |
| Signup (Photo) | `src/Screens/Auth/Signup/Photo/` | Profile photo upload |
| Signup (Invite) | `src/Screens/Auth/Signup/Invite/` | Invitation code entry |
| Forgot Password | `src/Screens/Auth/Forgot/` | Password reset request |
| Reset Password | `src/Screens/Auth/Reset/` | Password reset completion |
| Contact Verification | `src/Screens/Auth/Verification/Contact/` | Email/phone verification |
| 2FA Verification | `src/Screens/Auth/Verification/TFA/` | Two-factor authentication code entry |

### Feed & Content Screens (6)

| Screen | Path | Purpose |
|--------|------|---------|
| Feeds | `src/Screens/Feeds/` | Main feed (timeline of posts) |
| Post Detail | `src/Screens/Post/` | Single post view with comments |
| Post Create | `src/Screens/Post/Create/` | New post creation (text, image, video) |
| Search | `src/Screens/Search/` | User and content search |
| Hashtag | `src/Screens/Hashtag/` | Hashtag feed view |
| Report | `src/Screens/Report/` | Report content/user |

### Messaging Screens (2)

| Screen | Path | Purpose |
|--------|------|---------|
| Messages List | `src/Screens/Messages/` | Conversation list |
| Chat | `src/Screens/Messages/Chat/` | Real-time chat (WebSocket) |

### Account Screens (16)

| Screen | Path | Purpose |
|--------|------|---------|
| Account Overview | `src/Screens/Account/` | Account hub/dashboard |
| Profile | `src/Screens/Account/Profile/` | User profile view |
| Profile Edit | `src/Screens/Account/Profile/Edit/` | Edit profile details |
| Posts (My) | `src/Screens/Account/Posts/` | User's own posts list |
| Followers | `src/Screens/Account/Followers/` | Follower/following lists |
| Billing | `src/Screens/Account/Billing/` | Subscription/billing overview |
| Billing Card | `src/Screens/Account/Billing/Card/` | Payment card management |
| Settings | `src/Screens/Account/Settings/` | Settings hub |
| Settings Edit | `src/Screens/Account/Settings/Edit/` | Edit account settings |
| Blocking | `src/Screens/Account/Settings/Blocking/` | Blocked users management |
| Contact Settings | `src/Screens/Account/Settings/Contact/VerifyPassword/` | Contact change (verify password) |
| Phone Verify | `src/Screens/Account/Settings/Contact/VerifyPhone/` | Phone number verification |
| Account Deletion | `src/Screens/Account/Settings/Deletion/` | Account deletion flow |
| 2FA Settings | `src/Screens/Account/Settings/TFA/` | Enable/disable 2FA |
| 2FA Verify Code | `src/Screens/Account/Settings/TFA/VerifyCode/` | 2FA setup code verification |
| 2FA Verify Password | `src/Screens/Account/Settings/TFA/VerifyPassword/` | 2FA setup password confirmation |
| Support | `src/Screens/Account/Support/` | Support/help screen |

### Media Screens (3)

| Screen | Path | Purpose |
|--------|------|---------|
| Camera | `src/Screens/Media/Camera/` | Camera capture (photo/video) |
| Photos | `src/Screens/Media/Photos/` | Photo gallery picker |
| Preview | `src/Screens/Media/Preview/` | Media preview before posting |

### Utility Screens (4)

| Screen | Path | Purpose |
|--------|------|---------|
| Loader | `src/Screens/Loader/` | App loading/splash screen |
| Welcome | `src/Screens/Loader/Welcome/` | Onboarding welcome screen |
| Notifications | `src/Screens/Notifications/` | Notification list |
| Notification Details | `src/Screens/Mixed/NotificationDetails.js` | Single notification detail |

### Mixed Screens (2)

| Screen | Path | Purpose |
|--------|------|---------|
| Contacts | `src/Screens/Mixed/Contacts.js` | Contact list/invite friends |
| Suggest to Follow | `src/Screens/Mixed/SuggestToFollow.js` | Follow suggestions |

---

## Components (29 total)

| Component | Path | Purpose |
|-----------|------|---------|
| Agreement | `src/Components/Agreement/` | Terms of service / privacy policy agreement |
| Button (Standard) | `src/Components/Button/Standard/` | Primary action button |
| Button (Follow) | `src/Components/Button/Follow/` | Follow/unfollow toggle button |
| Button (Social/Apple) | `src/Components/Button/Social/Apple.js` | Apple Sign-In button |
| Button (Social/Email) | `src/Components/Button/Social/Email.js` | Email sign-in button |
| Button (Social/Facebook) | `src/Components/Button/Social/Facebook.js` | Facebook login button |
| Button (Social/Google) | `src/Components/Button/Social/Google.js` | Google login button |
| Chart | `src/Components/Chart/` | Data visualization chart |
| Collapsible | `src/Components/Collapsible/` | Expandable/collapsible section |
| Digit Input | `src/Components/Fields/Input/Digits/` | OTP/verification code input |
| Select | `src/Components/Fields/Select/` | Dropdown select field |
| Filler | `src/Components/Filler/` | Empty state placeholder |
| Header | `src/Components/Header/` | Screen header bar |
| Header (Custom) | `src/Components/Header/Custom/` | Custom header variant |
| Media File | `src/Components/Media/File/` | File attachment display |
| Media Image | `src/Components/Media/Image/` | Image display with loading |
| IcoMoon | `src/Components/Media/Image/IcoMoon/` | Custom icon font (IcoMoon) |
| Media Video | `src/Components/Media/Video/` | Video player component |
| Modal | `src/Components/Modal/` | Modal dialog overlay |
| Navigation | `src/Components/Navigation/` | Bottom tab navigation bar |
| People | `src/Components/People/` | User list item (followers, search results) |
| Permission | `src/Components/Permission/` | Permission request prompts (camera, notifications) |
| Post | `src/Components/Post/` | Post card (feed item) |
| Post Comments | `src/Components/Post/Comments/` | Comment list on post |
| Post Tag | `src/Components/Post/Tag/` | Hashtag tag chip |
| Preloader | `src/Components/Preloader/` | Loading spinner |
| Progress | `src/Components/Preloader/Progress/` | Progress bar (upload) |
| Timer | `src/Components/Timer/` | Countdown timer (OTP expiry) |
| User | `src/Components/User/` | User info display |
| User Avatar | `src/Components/User/Avatar/` | User avatar image |
| Validation Error | `src/Components/Validation/Error/` | Form error message |
| Validation Success | `src/Components/Validation/Success/` | Form success message |

---

## Navigation Structure

**File:** `src/Navigation/Navigator.js`

React Navigation stack + tab structure:

```
Root Navigator
├── Auth Stack
│   ├── Login
│   ├── Signup (multi-step: Form → Birth → Parent → Bio → Photo → Invite)
│   ├── Forgot Password
│   ├── Reset Password
│   └── Verification (Contact, 2FA)
├── Main Tab Navigator
│   ├── Home (Feeds)
│   ├── Search
│   ├── Create Post (+)
│   ├── Messages
│   └── Account
├── Modal Stack
│   ├── Post Detail
│   ├── Camera
│   ├── Photos
│   ├── Preview
│   ├── Hashtag
│   ├── Report
│   ├── Notifications
│   └── Chat
└── Loader / Welcome (initial)
```

---

## Redux Store

### Store Configuration

**File:** `src/Redux/Store.js`

### Reducers

| Reducer | File | State Shape |
|---------|------|-------------|
| Users | `src/Redux/Reducers/Users.js` | `{ currentUser, profile, followers, following, suggestions, blocked }` |
| Notifications | `src/Redux/Reducers/Notifications.js` | `{ items, unreadCount, loading }` |

### Actions

| Action Group | File | Purpose |
|-------------|------|---------|
| Users | `src/Redux/Actions/Users.js` | User CRUD, follow/unfollow, block, profile update |

### Containers (Redux connect HOCs)

| Container | File | Connected Screens |
|-----------|------|-------------------|
| Account | `src/Redux/Containers/Account.js` | Account-related screens |
| Auth | `src/Redux/Containers/Auth.js` | Auth flow screens |
| Mixed | `src/Redux/Containers/Mixed.js` | Shared/mixed screens |
| Tab | `src/Redux/Containers/Tab.js` | Tab navigation screens |

### Register

**File:** `src/Redux/Register.js` - Store registration and persistence setup

---

## API Models

| Model | File | Purpose |
|-------|------|---------|
| Auth | `src/Models/API/Auth.js` | Login, signup, password reset, 2FA API calls |
| Comments | `src/Models/API/Comments.js` | Comment CRUD API calls |
| Followers | `src/Models/API/Followers.js` | Follow/unfollow API calls |
| Posts | `src/Models/API/Posts.js` | Post CRUD, feed, like/unlike API calls |
| Users | `src/Models/API/Users.js` | User profile, settings, search API calls |

---

## Push Notifications

**File:** `src/Models/Notifications.js`

- Firebase Cloud Messaging (FCM) integration
- Push token registration on login
- Notification permission request flow (`src/Components/Permission/`)
- Local notification display
- Deep link handling from notification tap
- Notification badge count management

---

## WebSocket / Real-time

**File:** `src/Models/Socket.js`

- Socket.io client connection
- Real-time chat message delivery
- Online/offline status
- Typing indicators
- Connection management (reconnect on network change)

---

## Camera & Media Handling

| Feature | Location | Details |
|---------|----------|---------|
| Camera capture | `src/Screens/Media/Camera/` | Photo and video capture with flash toggle |
| Photo gallery | `src/Screens/Media/Photos/` | Device photo library picker |
| Media preview | `src/Screens/Media/Preview/` | Preview before uploading/posting |
| Image display | `src/Components/Media/Image/` | Cached image loading with placeholders |
| Video playback | `src/Components/Media/Video/` | In-feed and full-screen video player |
| File handling | `src/Components/Media/File/` | Document/file attachment display |

---

## Parental Consent Flow

**Path:** `src/Screens/Auth/Signup/Parent/`

1. During signup, birth date is collected (`Birth` screen)
2. If user is under age threshold, redirected to `Parent` screen
3. Parent email/phone collected for consent verification
4. Consent request sent to parent
5. Account remains pending until parent approves
6. Linked to `Agreement` component for terms acceptance

---

## Localization

| File | Language |
|------|----------|
| `src/Data/Locale/US.js` | English (US) |
| `src/Data/Locale/PT.js` | Portuguese |
| `src/Data/Locale/index.js` | Locale registry |

---

## Other Data

| File | Purpose |
|------|---------|
| `src/Data/Countries.js` | Country list with codes and dial codes |
| `src/Data/Slack/Template.js` | Slack notification templates |

---

## Assets

- **Country flags:** 252 SVG flag icons (`src/Assets/Images/Flags/`)
- **UI icons:** 70+ SVG icons (`src/Assets/Images/`)
- **Illustrations:** 3 onboarding illustrations (`src/Assets/Images/Illustration/`)
- **Custom font:** IcoMoon icon font (`assets/fonts/icomoon.ttf`)

---

## Native Bridge

### iOS
- `ios/Bhapi.swift` / `ios/Bhapi-Bridging-Header.h` - Swift-ObjC bridge
- Firebase configured via `GoogleService-Info.plist`
- Entitlements: `ios/Bhapi/Bhapi.entitlements` (push notifications, associated domains)

### Android
- Custom native module: `AndroidNativeModule.java` / `AndroidNativePackage.java`
- Firebase configured via `google-services.json`
- ProGuard rules for release builds

---

## Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| react-native | 0.64.2 | Mobile framework |
| axios | 0.21.x | HTTP client |
| redux | (store) | State management |
| react-navigation | (Navigator) | Screen navigation |
| socket.io-client | (Socket.js) | Real-time messaging |
| firebase/messaging | (Notifications) | Push notifications |
| react-native-camera | (Camera screen) | Camera access |
| react-native-svg | (Flag/icon rendering) | SVG rendering |
| react-native-vector-icons | (fonts) | Icon fonts |

---

## Build & Configuration

| File | Purpose |
|------|---------|
| `package.json` | Dependencies and scripts |
| `app.json` | React Native app configuration |
| `babel.config.js` | Babel transpilation config |
| `metro.config.js` | Metro bundler config |
| `.eslintrc.js` | ESLint rules |
| `.prettierrc.js` | Code formatting |
| `react-native.config.js` | RN CLI configuration |
| `webpack.config.js` | Web build config |
| `web/index.html` | Web entry point (React Native Web) |

---

## Open Pull Requests (8 total)

### Snyk Security PRs (8)

Automated dependency vulnerability fix PRs from Snyk bot, including one PR covering 34 vulnerabilities across multiple transitive dependencies. Key vulnerability areas include:
- Prototype pollution in lodash/underscore
- Regular expression denial of service (ReDoS)
- Server-side request forgery (SSRF)
- Arbitrary code execution in dependency chains

---

## Key Architecture Notes

1. **Entry point:** `index.js` -> `src/App.js` (root component with Redux Provider and Navigator)
2. **State management:** Redux with connect HOCs (not hooks-based), 4 container files
3. **API layer:** Axios-based API models in `src/Models/API/` (5 modules)
4. **Config:** `src/Config/index.js` - API base URL, environment detection
5. **Helpers:** `src/Models/Helpers/index.js` - Utility functions
6. **Web support:** `src/Models/Web.js` + `webpack.config.js` - React Native Web configuration
7. **No test files:** No test directory found in the repository
8. **Security review:** `CODE_REVIEW_REPORT.md` present at root
