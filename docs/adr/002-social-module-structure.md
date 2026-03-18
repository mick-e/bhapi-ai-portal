# ADR-002: Social Module Structure

## Status: Accepted

## Date: 2026-03-17

## Context

The unified Bhapi Platform requires social features to support community interaction: posts, comments, followers, direct messaging, and user/content search. These features are central to the platform's value proposition and will be used across both the family safety (AI Portal) and developer community (former Bhapi App) contexts.

The existing AI Portal backend (`src/main.py`) already contains 19 well-structured modules (~190 routes) following a consistent pattern: each module lives in its own directory under `src/` and contains `router.py`, `service.py`, `models.py`, and `schemas.py`. The backend uses FastAPI with SQLAlchemy async, Alembic migrations, and PostgreSQL.

We need to decide where and how to build the social features.

## Decision

Build social features as new modules within the existing FastAPI backend, following the established module pattern under `src/social/`.

The module structure will be:

```
src/social/
    __init__.py
    posts/
        router.py      # CRUD endpoints, feed, likes
        service.py      # Business logic, feed algorithms
        models.py       # Post, PostLike, PostMedia
        schemas.py      # Pydantic request/response models
    comments/
        router.py       # Threaded comments, reactions
        service.py
        models.py       # Comment, CommentReaction
        schemas.py
    followers/
        router.py       # Follow/unfollow, follower lists
        service.py
        models.py       # Follow relationship
        schemas.py
    messaging/
        router.py       # Conversations, messages
        service.py      # Encryption, delivery
        models.py       # Conversation, Message, Participant
        schemas.py
    search/
        router.py       # Unified social search
        service.py      # PostgreSQL FTS integration
        schemas.py
```

Each module will:

- Register its router in `src/main.py` under the `/api/v1/social/` prefix.
- Use the existing RBAC system (`require_permission()`) with new social-specific permissions.
- Share the existing database session, user model, and tenant isolation infrastructure.
- Add Alembic migrations for new tables.
- Include content moderation hooks for child safety (leveraging the existing risk assessment engine).

## Consequences

**Positive:**

- Consistent patterns across the entire codebase. New developers learn one module, they know them all.
- Shared infrastructure: auth, RBAC, rate limiting, logging, error handling, CORS, and middleware are inherited automatically.
- Single deployment unit. No inter-service networking, no API gateway, no distributed tracing needed.
- Content moderation for child safety can reuse the existing 14-category risk taxonomy and AI safety scoring.
- PostgreSQL FTS with GIN indexes (already proven in the codebase) handles social search without a separate search service.
- Testing infrastructure (fixtures, factories, async test session) is reused directly.

**Negative:**

- The monolith grows larger. The `src/` directory will expand from 19 to ~24 modules.
- Social features with high write volume (messaging, feeds) share the same database connection pool as safety-critical features (risk assessment, alerts).
- If social features require real-time capabilities (WebSocket for chat), the existing deployment may need adjustment for persistent connections.

**Mitigations:**

- Database connection pool sizing can be tuned per-workload via configuration.
- WebSocket support can be added to FastAPI without architectural changes (it supports WebSocket natively).
- If social write volume becomes a bottleneck, read replicas can be introduced at the database level without changing application code.

## Alternatives Considered

### Separate Microservice

- **Pros**: Independent scaling, independent deployment, isolated failure domain. Team can use a different tech stack if desired.
- **Cons**: Requires API gateway or service mesh for routing. Cross-service auth token validation adds latency. Shared user model requires either data duplication or synchronous cross-service calls. Separate CI/CD pipeline, separate monitoring, separate database. Content moderation for child safety would need to call back to the AI Portal's risk engine over the network, adding latency and a failure point in a safety-critical path.
- **Rejected because**: The operational complexity is not justified at current scale. The team is small, the deployment target is a single Render service, and the content moderation integration is too important to separate by a network boundary.

### GraphQL Layer

- **Pros**: Flexible queries for social feeds (clients request exactly the fields they need). Good fit for relationship-heavy data (followers, threads). Strong ecosystem (Apollo, Relay).
- **Cons**: Introduces a second API paradigm alongside the existing REST API. N+1 query problems require DataLoader patterns. Authorization must be implemented separately from the existing `require_permission()` system. The frontend (Next.js + React Query) is already built around REST patterns; adding GraphQL means maintaining two data-fetching strategies. Adds complexity without clear benefit given the team size.
- **Rejected because**: The cognitive overhead of maintaining two API paradigms (REST + GraphQL) outweighs the query flexibility benefits. REST with well-designed endpoints and pagination covers the social use cases adequately.
