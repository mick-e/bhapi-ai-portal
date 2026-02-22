/**
 * Bhapi AI Safety Monitor — HMAC-SHA256 Signing
 *
 * Uses the Web Crypto API (SubtleCrypto) which is available in both
 * service workers and content script contexts.
 *
 * Firefox equivalent: the same `crypto.subtle` API is available under
 * the standard Web Crypto interface — no `browser.*` shim needed.
 */

/**
 * Encode a string as a UTF-8 Uint8Array.
 */
function encodeUtf8(text: string): Uint8Array {
  return new TextEncoder().encode(text);
}

/**
 * Convert an ArrayBuffer to a lowercase hex string.
 */
function bufferToHex(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  const hexParts: string[] = [];
  for (const byte of bytes) {
    hexParts.push(byte.toString(16).padStart(2, "0"));
  }
  return hexParts.join("");
}

/**
 * Import a string secret as an HMAC CryptoKey.
 */
async function importHmacKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "raw",
    encodeUtf8(secret),
    { name: "HMAC", hash: "SHA-256" },
    false, // not extractable
    ["sign"],
  );
}

/**
 * Sign a payload string with an HMAC-SHA256 secret and return the
 * hex-encoded signature.
 *
 * @param payload - The string payload to sign (typically JSON).
 * @param secret  - The shared HMAC secret.
 * @returns A lowercase hex-encoded HMAC-SHA256 signature.
 */
export async function signPayload(payload: string, secret: string): Promise<string> {
  const key = await importHmacKey(secret);
  const signature = await crypto.subtle.sign("HMAC", key, encodeUtf8(payload));
  return bufferToHex(signature);
}

/**
 * Verify an HMAC-SHA256 signature for a payload.
 *
 * @param payload   - The original string payload.
 * @param secret    - The shared HMAC secret.
 * @param signature - The hex-encoded signature to verify.
 * @returns true if the signature is valid.
 */
export async function verifySignature(
  payload: string,
  secret: string,
  signature: string,
): Promise<boolean> {
  const expected = await signPayload(payload, secret);
  // Constant-time comparison is not critical here (client-side only),
  // but we still avoid short-circuit comparison.
  if (expected.length !== signature.length) return false;
  let result = 0;
  for (let i = 0; i < expected.length; i++) {
    result |= expected.charCodeAt(i) ^ signature.charCodeAt(i);
  }
  return result === 0;
}
