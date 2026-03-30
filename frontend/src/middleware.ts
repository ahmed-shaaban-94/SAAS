import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getToken } from "next-auth/jwt";

/** Paths that do not require authentication. */
const PUBLIC_PATHS = [
  "/login",
  "/api/auth",
  "/",           // Marketing landing page
  "/terms",
  "/privacy",
];

/** Check if the request path starts with any public prefix. */
function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some(
    (p) => pathname === p || pathname.startsWith(p + "/"),
  );
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // --- Auth check (skip for public paths & static assets) ---
  if (!isPublicPath(pathname)) {
    const token = await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    });

    if (!token) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("callbackUrl", request.url);
      return NextResponse.redirect(loginUrl);
    }
  }

  // --- Security headers ---
  const response = NextResponse.next();
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const keycloakIssuer =
    process.env.KEYCLOAK_ISSUER || "http://localhost:8080/realms/datapulse";
  // Extract origin from issuer (e.g. "http://localhost:8080")
  const keycloakOrigin = new URL(keycloakIssuer).origin;
  const isDev = process.env.NODE_ENV === "development";

  // Next.js requires 'unsafe-inline' for styles (CSS-in-JS / Tailwind injection).
  // Dev mode additionally needs 'unsafe-eval' for React Refresh / HMR.
  const scriptSrc = isDev
    ? "script-src 'self' 'unsafe-inline' 'unsafe-eval'"
    : "script-src 'self' 'unsafe-inline'";

  response.headers.set(
    "Content-Security-Policy",
    [
      "default-src 'self'",
      scriptSrc,
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: https:",
      "font-src 'self'",
      `connect-src 'self' ${apiUrl} ${keycloakOrigin}`,
      "frame-ancestors 'none'",
      "base-uri 'self'",
      `form-action 'self' ${keycloakOrigin}`,
    ].join("; "),
  );

  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");

  return response;
}

export const config = {
  matcher: "/((?!_next/static|_next/image|favicon.ico).*)",
};
