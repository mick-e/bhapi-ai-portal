# ADR-008: Separate WebSocket Real-Time Service

## Status: Accepted

## Date: 2026-03-19

## Context

The Bhapi Social app (ADR-006) requires real-time features:

- **Messaging:** Instant message delivery between children (with moderation).
- **Typing indicators:** Show when a contact is typing.
- **Presence:** Online/offline/away status for friends.
- **Live feed updates:** New posts, reactions, and comments appear without polling.
- **Upload status:** Media processing progress (ADR-007) pushed to client.

WebSocket connections have fundamentally different scaling characteristics than REST API requests:

| Characteristic | REST Request | WebSocket Connection |
|---------------|-------------|---------------------|
| Duration | Milliseconds | Minutes to hours |
| Memory per client | ~0 (stateless) | ~50KB (connection state, buffers) |
| DB connections | Acquired per-request, released immediately | Potentially held for connection lifetime |
| CPU pattern | Burst (request handling) | Idle with occasional spikes (message relay) |
| Scaling trigger | Requests per second | Concurrent connections |

Mixing long-lived WebSocket connections with the REST API monolith means that WebSocket connection count directly impacts REST API latency (shared thread pool, shared DB connection pool, shared memory).

## Decision

Deploy a separate FastAPI WebSocket service as its own Render web service.

### Service Architecture

```
┌──────────────┐     ┌──────────────┐
│  core-api    │     │  realtime    │
│  (REST)      │◄───►│  (WebSocket) │
│  Port 8000   │     │  Port 8001   │
│  Pool: 20    │     │  Pool: 10    │
└──────┬───────┘     └──────┬───────┘
       │                     │
       ▼                     ▼
┌──────────────┐     ┌──────────────┐
│  PostgreSQL  │     │    Redis     │
│  (shared)    │     │  (pub/sub)   │
└──────────────┘     └──────────────┘
```

### Source Location
- `src/realtime/` — new module in the existing repository (not a separate repo).
- Separate Dockerfile target or entrypoint for the WebSocket service.
- Deployed as a second web service in `render.yaml`.

### Database Connection Strategy
- **Pool limit: 10 connections** with lazy acquisition.
- Connections are NOT held per WebSocket session. A connection is acquired from the pool only when a database write is needed (e.g., persisting a message), then immediately released.
- Read-heavy operations (presence, typing indicators) use Redis, not PostgreSQL.
- Total connection budget: monolith 20 + jobs 5 + WebSocket 10 = 35, well within Render Standard plan's 50-connection limit.

### Inter-Service Communication
- **Redis pub/sub** for cross-service events:
  - `core-api` publishes: new alert, moderation result, media processed, blocking rule change.
  - `realtime` publishes: message sent (for persistence by core-api jobs).
  - `realtime` subscribes: pushes events to connected clients.
- Redis channel naming: `bhapi:{event_type}:{target_id}` (e.g., `bhapi:alert:group_123`).

### Authentication
- Same JWT secret as the monolith. WebSocket connection handshake validates JWT token passed as query parameter (`?token=...`).
- Token refresh: client disconnects and reconnects with new token (WebSocket does not support mid-connection header changes).

### Protocol
- JSON messages over WebSocket (not binary protocol).
- Message types: `message`, `typing`, `presence`, `feed_update`, `media_status`, `alert`, `system`.
- Client heartbeat every 30 seconds. Server disconnects after 90 seconds of silence.

## Consequences

**Positive:**

- Independent scaling. WebSocket connections do not impact REST API latency or connection pool.
- Resource isolation. A spike in real-time connections (e.g., during school hours) does not degrade dashboard performance for parents.
- Can horizontally scale the WebSocket service via Redis pub/sub. Multiple WebSocket instances share state through Redis, not in-process memory.
- Cleaner failure modes. If the WebSocket service crashes, the REST API and all existing features continue working. Real-time features degrade gracefully to polling.

**Negative:**

- Operational complexity. A second service to deploy, monitor, and debug. Two sets of logs, two health checks, two scaling configurations.
- Redis becomes a critical dependency for inter-service communication. Redis downtime means real-time features stop working (REST API unaffected).
- Deployment coordination. Schema changes that affect both services must be deployed in the correct order (migration first, then both services).

**Risks:**

- Database connection exhaustion. **Mitigation:** Lazy acquisition (no persistent connections per WebSocket session). Total pool: 35 out of 50 limit, leaving 15 connections as headroom. Connection pool monitoring via health check endpoint.
- Redis pub/sub message loss (Redis pub/sub does not guarantee delivery). **Mitigation:** Messages are persisted to PostgreSQL by the core-api jobs worker. Real-time delivery is best-effort; clients fetch missed messages on reconnect via REST API.
- WebSocket reconnection storms after service restart. **Mitigation:** Exponential backoff with jitter on client reconnection (initial 1s, max 30s, +/- 50% jitter).

## Alternatives Considered

### WebSocket Connections in the Monolith

- **Pros:** Simpler deployment. No inter-service communication needed.
- **Cons:** WebSocket connections compete with REST requests for the same database connection pool, thread pool, and memory. At 500 concurrent connections (~50KB each = 25MB), the monolith's REST latency would degrade. Scaling the monolith to handle WebSocket load wastes resources on REST capacity that is not needed.
- **Rejected because:** The scaling characteristics are too different. Mixing them creates cascading failure modes.

### Third-Party Real-Time Service (Pusher, Ably, Firebase)

- **Pros:** No infrastructure to manage. Built-in scaling. SDKs for mobile.
- **Cons:** Per-message pricing becomes expensive for a social app with high message volume. Data leaves the platform (privacy concern for children's messages). Vendor lock-in with no self-hosted fallback. Cannot integrate with moderation pipeline without extra latency (message goes to vendor, vendor delivers to client, separately: message goes to moderation).
- **Rejected because:** Children's message data must stay within the platform's control. Per-message pricing is unpredictable for a social app.

## Related ADRs

- [ADR-003](003-mongodb-to-postgresql.md) — Single PostgreSQL database (shared by both services)
- [ADR-006](006-two-app-mobile-strategy.md) — Social app requires real-time features
- [ADR-007](007-cloudflare-media-storage.md) — Media upload status delivered via WebSocket
