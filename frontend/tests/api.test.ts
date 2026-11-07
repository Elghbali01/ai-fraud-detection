import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiRequest } from "@/lib/api";

afterEach(() => vi.unstubAllGlobals());

describe("real API client failure semantics", () => {
  it("preserves sanitized validation errors and request IDs", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      error: "invalid_request",
      message: "Request validation failed.",
      request_id: "test-request-id",
      timestamp: "2026-01-01T00:00:00Z",
    }), { status: 422, headers: { "Content-Type": "application/json" } })));

    await expect(apiRequest("/predictions", { method: "POST", body: "{}" })).rejects.toMatchObject({
      name: "ApiError",
      status: 422,
      code: "invalid_request",
      requestId: "test-request-id",
      message: "Request validation failed.",
    });
  });

  it("maps a network failure to an explicit offline error, without mock fallback", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("connection refused")));
    let thrown: unknown;
    try { await apiRequest("/health"); } catch (error) { thrown = error; }
    expect(thrown).toBeInstanceOf(ApiError);
    expect(thrown).toMatchObject({ status: 0, code: "api_unreachable" });
    expect((thrown as Error).message).toContain("Cannot reach the local API");
  });
});
