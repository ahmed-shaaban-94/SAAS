import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getToken } from "next-auth/jwt";

/** Paths that do not require authentication. */
const PUBLIC_PATHS = [
  "/login",
  "/api/auth",
  "/api/dev-login", // TEMP: dev bypass
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
  const auth0Domain = process.env.AUTH0_DOMAIN || "";
  const auth0Origin = auth0Domain ? `https://${auth0Domain}` : "";
  const isDev = process.env.NODE_ENV === "development";

  // Next.js requires 'unsafe-inline' for styles (CSS-in-JS / Tailwind injection).
  // Dev mode additionally needs 'unsafe-eval' for React Refresh / HMR.
  // API calls now go through Traefik on same origin — no extra connect-src needed.
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
      `connect-src 'self'${auth0Origin ? ` ${auth0Origin}` : ""}`,
      "frame-ancestors 'none'",
      "base-uri 'self'",
      `form-action 'self'${auth0Origin ? ` ${auth0Origin}` : ""}`,
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
