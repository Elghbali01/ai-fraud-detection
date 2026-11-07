import type { ApiErrorPayload } from "@/lib/types";

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_FRAUD_API_URL ?? "http://127.0.0.1:8000/api/v1"
).replace(/\/$/, "");

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId?: string;

  constructor(status: number, payload: ApiErrorPayload) {
    super(payload.message || payload.error || `API request failed (${status})`);
    this.name = "ApiError";
    this.status = status;
    this.code = payload.error || "request_failed";
    this.requestId = payload.request_id;
  }
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, {
      error: "api_unreachable",
      message: `Cannot reach the local API at ${API_BASE_URL}. Start it with scripts/start-api.ps1 and retry.`,
    });
  }

  const payload = (await response.json().catch(() => null)) as unknown;
  if (!response.ok) {
    const apiError = typeof payload === "object" && payload !== null ? payload : {};
    throw new ApiError(response.status, apiError as ApiErrorPayload);
  }
  return payload as T;
}
