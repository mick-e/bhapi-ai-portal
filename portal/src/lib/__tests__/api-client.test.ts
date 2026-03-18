import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ApiRequestError, apiFetch } from "../api-client";

// Save original fetch
const originalFetch = globalThis.fetch;

describe("apiFetch", () => {
  beforeEach(() => {
    vi.stubGlobal("localStorage", {
      getItem: vi.fn().mockReturnValue(null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("makes GET requests with correct headers", async () => {
    const mockResponse = { data: "test" };
    globalThis.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockResponse),
    });

    const result = await apiFetch("/api/v1/test");

    // In jsdom, window is defined so BASE_URL = "" (same-origin)
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/test"),
      expect.objectContaining({
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
        credentials: "include",
      })
    );
    expect(result).toEqual(mockResponse);
  });

  it("includes auth token when available", async () => {
    vi.mocked(localStorage.getItem).mockReturnValue("test-token");
    globalThis.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });

    await apiFetch("/api/v1/test");

    expect(fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer test-token",
        }),
      })
    );
  });

  it("throws ApiRequestError on non-ok response", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      statusText: "Unprocessable Entity",
      json: () => Promise.resolve({ detail: "Validation failed" }),
    });

    await expect(apiFetch("/api/v1/test")).rejects.toThrow(ApiRequestError);
  });

  it("includes status and detail on ApiRequestError", async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      status: 403,
      statusText: "Forbidden",
      json: () => Promise.resolve({ detail: "Access denied" }),
    });

    const error = await apiFetch("/api/v1/test").catch((err) => err);
    expect(error).toBeInstanceOf(ApiRequestError);
    expect(error.status).toBe(403);
    expect(error.detail).toBe("Access denied");
  });

  it("returns undefined for 204 responses", async () => {
    globalThis.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      status: 204,
    });

    const result = await apiFetch("/api/v1/test");
    expect(result).toBeUndefined();
  });
});

describe("ApiRequestError", () => {
  it("has correct properties", () => {
    const error = new ApiRequestError(404, "Not found");
    expect(error.status).toBe(404);
    expect(error.detail).toBe("Not found");
    expect(error.message).toBe("Not found");
    expect(error.name).toBe("ApiRequestError");
  });
});
