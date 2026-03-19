# ADR-007: Cloudflare R2/Images/Stream for Media Storage

## Status: Accepted

## Date: 2026-03-19

## Context

The Bhapi Social app (ADR-006) requires user-generated media storage for a children's social network:

- **Images:** Profile photos, post images, creative tool outputs. Need automatic resizing (thumbnail 150px, medium 600px, full 1200px) and format optimization (WebP/AVIF).
- **Videos:** Short-form video posts and messages. Need transcoding to adaptive streaming formats (HLS/DASH) for reliable playback across devices and network conditions.
- **CDN delivery:** Global distribution for low-latency media loading.
- **Content moderation integration:** All uploaded media must pass through the safety pipeline (CSAM detection, safety classification) before becoming visible. This requires webhook-based integration between the storage provider and the backend moderation service.

Cost is a significant concern. AWS S3 egress fees ($0.09/GB) become substantial for a media-heavy social app serving children globally. A children's social network will have high read-to-write ratios (many views per upload), making egress the dominant cost.

## Decision

Use the Cloudflare media stack:

### Cloudflare R2 (Object Storage)
- General-purpose storage for all uploaded media (originals, processed variants, documents).
- Zero egress fees. Pay only for storage ($0.015/GB/month) and operations.
- S3-compatible API for easy migration if needed.

### Cloudflare Images (Image Processing)
- Automatic resize and optimization on upload.
- Three named variants: `thumbnail` (150px, fit crop), `medium` (600px, fit scale-down), `full` (1200px, fit scale-down).
- Automatic WebP/AVIF delivery based on client Accept header.
- Direct creator uploads via pre-signed URLs (no backend proxying of image bytes).

### Cloudflare Stream (Video Transcoding)
- Automatic transcoding to HLS/DASH adaptive bitrate streaming.
- Built-in player embed or raw HLS URL for custom player.
- Direct creator uploads via TUS protocol (resumable uploads for mobile).
- Webhook notification on transcode completion.

### Upload Flow
1. Client requests pre-signed upload URL from backend (`POST /api/v1/media/upload-url`).
2. Backend generates URL, creates `media_uploads` record with status `pending_moderation`.
3. Client uploads directly to Cloudflare (no backend proxying).
4. Cloudflare sends webhook to backend on processing completion.
5. Backend triggers moderation pipeline (CSAM scan, safety classification).
6. On moderation pass, status changes to `approved` and media URL becomes accessible.
7. On moderation fail, status changes to `rejected`, media is deleted from Cloudflare, and alert is generated.

### Backend Integration
- New `src/media/` module following existing module conventions.
- `media_uploads` table: `id`, `user_id`, `group_id`, `cloudflare_id`, `media_type` (image/video), `status` (pending_moderation/approved/rejected), `moderation_result`, `created_at`.
- Cloudflare webhook endpoint with signature verification.
- Pre-signed URL generation via Cloudflare API.

## Consequences

**Positive:**

- Zero egress fees eliminate the largest variable cost for a media-heavy social app. At scale, this saves thousands per month compared to S3.
- Global CDN included with R2/Images/Stream. No separate CDN configuration needed.
- Automatic image resizing and video transcoding eliminate custom processing infrastructure.
- Webhook integration fits naturally into the existing moderation pipeline architecture.
- Pre-signed uploads mean media bytes never touch the backend, reducing bandwidth and compute costs.
- S3-compatible API provides a migration path if Cloudflare becomes unsuitable.

**Negative:**

- Vendor lock-in to Cloudflare for Images and Stream APIs (R2 is S3-compatible, so less locked in).
- New operational dependency. Cloudflare outages would affect media delivery (mitigated: text content remains available via PostgreSQL).
- Three Cloudflare products to configure and monitor (R2, Images, Stream) instead of one (S3).

**Risks:**

- Cost at scale needs monitoring. While egress is free, per-operation costs and Images/Stream pricing could surprise at high volume. **Mitigation:** Set up billing alerts at $50, $100, $500 thresholds. Review monthly.
- Cloudflare reliability or policy changes. **Mitigation:** R2 is S3-compatible, so fallback to S3 + CloudFront is achievable. Images and Stream would require more work to replace (custom Lambda@Edge or similar).
- CSAM detection latency. If the moderation pipeline is slow, media appears delayed to users. **Mitigation:** Target <5s moderation SLA; show "processing" placeholder in UI.

## Related ADRs

- [ADR-006](006-two-app-mobile-strategy.md) — Social app requires media storage
- [ADR-008](008-websocket-realtime-service.md) — Real-time service delivers media URLs and upload status via WebSocket
