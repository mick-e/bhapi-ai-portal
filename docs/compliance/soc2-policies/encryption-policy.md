# Encryption Policy

**Version:** 1.0
**Effective Date:** 2026-03-24
**Category:** Confidentiality (C1 — Confidential Information)
**Owner:** Engineering Lead
**Review Cycle:** Annual

---

## 1. Purpose

This policy describes how Bhapi Family AI Governance Platform protects data at rest and in transit using encryption. It maps to SOC 2 Trust Services Criteria C1.1 (Confidential information identified) and CC6.7 (Transmission controls).

---

## 2. Data at Rest

### 2.1 Primary Encryption Mechanism
All sensitive credential fields (third-party API keys, PII-adjacent data) are encrypted using **Fernet symmetric encryption** (`cryptography` library) before being written to the database. The implementation lives in `src/encryption.py`.

- Key: Derived from `SECRET_KEY` environment variable using PBKDF2-HMAC-SHA256 with a fixed salt, then Base64url-encoded to meet Fernet's key format requirement.
- Cipher: AES-128-CBC with PKCS7 padding and HMAC-SHA256 for integrity.
- Format: Fernet token includes timestamp — enables key-version-aware rotation.

### 2.2 Cloud KMS (Optional)
When `GCP_PROJECT_ID` is set, the platform uses **Google Cloud KMS** as an envelope encryption wrapper:
- Data encryption key (DEK) generated locally.
- DEK is encrypted with a KMS key encryption key (KEK) and stored alongside ciphertext.
- Provides hardware-security-module (HSM) protection for the root key.

### 2.3 Content Excerpts
- AI conversation content excerpts are encrypted at capture time via `encrypt_credential()`.
- Decrypted only for display to the authorised parent/admin.
- TTL-based purge job runs daily — excerpts older than the configured retention window are permanently deleted.

### 2.4 Database Passwords
- User passwords hashed with **bcrypt** (cost factor 12) — one-way hash, not reversible.
- Stored in `users.password_hash` column.

### 2.5 API Keys
- Third-party spend-provider API keys (OpenAI, Anthropic, Google, Microsoft, xAI) stored with Fernet encryption.
- Platform API keys (`bhapi_sk_*`) stored as SHA-256 hashes only — plaintext never persisted after creation.

---

## 3. Data in Transit

### 3.1 TLS Enforcement
- All external traffic is routed through **Render's managed ingress**, which terminates TLS 1.2 or later.
- HTTP-only connections are redirected to HTTPS automatically.
- HSTS header (`Strict-Transport-Security`) is set by `SecurityHeadersMiddleware` with `max-age=31536000; includeSubDomains; preload`.

### 3.2 Internal Service Communication
- WebSocket real-time service (`src/realtime/`) communicates over the same TLS-protected channel.
- Redis pub/sub (internal) is deployed on the same private network segment as the API — not exposed to the public internet.

### 3.3 Third-Party API Calls
- All outbound API calls use `httpx.AsyncClient` with system CA bundle verification enabled (default behaviour).
- Certificate pinning is not currently implemented — subject to annual review.

---

## 4. Key Management

### 4.1 Primary Secret Key
| Property | Value |
|----------|-------|
| Storage | Render environment variable (`SECRET_KEY`) |
| Minimum length | 32 characters in production |
| Rotation trigger | Compromise, annual review, or engineer offboarding |
| Rotation procedure | (1) Generate new key, (2) update Render env var, (3) redeploy, (4) re-encrypt existing secrets |

### 4.2 KMS Keys (GCP)
- KMS key rings managed in GCP IAM with least-privilege service account.
- Key version rotation: automatic 90-day rotation policy.
- Disabled key versions retained for 7 days to allow emergency decryption of older blobs.

### 4.3 Backup Keys
- Encrypted database backups use the same Fernet key in effect at backup time.
- Backup encryption key material is archived separately from the backup itself.

---

## 5. Classification of Sensitive Data

| Data Type | Classification | Encryption |
|-----------|----------------|------------|
| User passwords | Confidential | bcrypt hash |
| Platform API keys | Confidential | SHA-256 hash |
| Third-party API keys | Confidential | Fernet encrypted |
| AI conversation excerpts | Sensitive | Fernet encrypted + TTL |
| Child date-of-birth | Sensitive | Fernet encrypted |
| Group metadata | Internal | Not encrypted (DB access controlled) |
| Audit logs | Internal | Not encrypted (immutable, DB access controlled) |

---

## 6. References

- SOC 2 CC6.7: Transmission and movement of information
- SOC 2 C1.1: Identification of confidential information
- GDPR Article 32: Security of processing (encryption as a technical measure)
- COPPA 2026: Data minimisation and security requirements for children's data
