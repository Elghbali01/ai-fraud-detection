import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const DEFAULT_API_URL = "http://127.0.0.1:8000/api/v1";
const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "::1", "[::1]"]);

function localApiOrigin(): string {
  try {
    const configured = new URL(process.env.NEXT_PUBLIC_FRAUD_API_URL ?? DEFAULT_API_URL);
    if (
      (configured.protocol === "http:" || configured.protocol === "https:") &&
      LOCAL_HOSTS.has(configured.hostname.toLowerCase())
    ) {
      return configured.origin;
    }
  } catch {
    // Keep the policy on its safe local default when the API URL is malformed.
  }
  return new URL(DEFAULT_API_URL).origin;
}

export function proxy(request: NextRequest) {
  const nonce = btoa(crypto.randomUUID());
  const development = process.env.NODE_ENV === "development";
  const csp = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${development ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' blob: data:",
    "font-src 'self' data:",
    `connect-src 'self' ${localApiOrigin()}`,
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ].join("; ");

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", csp);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", csp);
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  response.headers.set("Permissions-Policy", "camera=(), geolocation=(), microphone=()");
  return response;
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)"],
};
