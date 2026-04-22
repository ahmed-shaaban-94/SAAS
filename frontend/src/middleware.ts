import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getToken } from "next-auth/jwt";
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const AUTH_PROVIDER =
  (process.env.NEXT_PUBLIC_AUTH_PROVIDER as "auth0" | "clerk") || "auth0";

/**
 * Derive the Clerk Frontend API origin.
 *
 * Clerk's publishable key base64-encodes the host followed by a ``$``
 * sentinel (e.g. ``pk_test_b3JpZW50ZWQtbGFyay02OC5jbGVyay5hY2NvdW50cy5kZXYk``
 * decodes to ``oriented-lark-68.clerk.accounts.dev$``). Decoding means the
 * CSP allow-list stays correct even when the operator forgets to set
 * ``NEXT_PUBLIC_CLERK_FRONTEND_API``. The explicit env var wins if present.
 */
function clerkFrontendOrigin(): string {
  const explicit = process.env.NEXT_PUBLIC_CLERK_FRONTEND_API;
  if (explicit) return explicit.replace(/\/$/, "");

  const pk = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || "";
  const prefix = pk.startsWith("pk_test_") ? "pk_test_" : pk.startsWith("pk_live_") ? "pk_live_" : "";
  if (!prefix) return "";
  const encoded = pk.slice(prefix.length);
  try {
    // Global ``atob`` is available in Edge Runtime where middleware runs.
    const decoded = atob(encoded);
    const host = decoded.replace(/\$$/, "");
    return host ? `https://${host}` : "";
  } catch {
    return "";
  }
}

/** Paths that do not require authentication. */
const PUBLIC_PATHS = [
  "/login",
  "/sign-in",    // Clerk hosted sign-in route
  "/sign-up",    // Clerk hosted sign-up route
  "/api/auth",
  // dev-login removed — was a temporary dev bypass
  "/",           // Marketing landing page
  "/landing",    // Static landing page
  "/terms",
  "/privacy",
  "/embed",      // Public embed route — token-based auth handled at route level
  "/demo",       // Live demo — simulated data, no sign-in required
];

/** Check if the request path starts with any public prefix. */
function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some(
    (p) => pathname === p || pathname.startsWith(p + "/"),
  );
}

/**
 * Resolve custom domain / subdomain to tenant context.
 * Sets X-Tenant-Domain header so downstream pages can fetch public branding.
 */
function resolveTenantDomain(request: NextRequest): string | null {
  const host = request.headers.get("host") || "";
  const baseDomain = process.env.BASE_DOMAIN || "datapulse.tech";

  // Skip localhost / IP addresses
  if (host.startsWith("localhost") || host.startsWith("127.") || host.startsWith("10.")) {
    return null;
  }

  // Subdomain: *.datapulse.tech
  if (host.endsWith(`.${baseDomain}`)) {
    const subdomain = host.replace(`.${baseDomain}`, "").split(":")[0];
    if (subdomain && subdomain !== "www") {
      return subdomain;
    }
  }

  // Custom domain: anything that's not the base domain
  const hostname = host.split(":")[0];
  if (hostname !== baseDomain && hostname !== `www.${baseDomain}`) {
    return hostname;
  }

  return null;
}

/**
 * Add the shared tenant-domain header and CSP/security headers the app
 * always needs. Mutates the given response in place; returns it for
 * convenient `return applyCommonHeaders(...)` usage from both provider
 * branches.
 */
function applyCommonHeaders(
  response: NextResponse,
  tenantDomain: string | null,
): NextResponse {
  if (tenantDomain) {
    response.headers.set("X-Tenant-Domain", tenantDomain);
  }

  const auth0Domain = process.env.AUTH0_DOMAIN || "";
  const auth0Origin = auth0Domain ? `https://${auth0Domain}` : "";
  const clerkOrigin = AUTH_PROVIDER === "clerk" ? clerkFrontendOrigin() : "";
  const isDev = process.env.NODE_ENV === "development";

  // Allow scripts from Clerk when active — Clerk injects its JS from its
  // own CDN (e.g. https://oriented-lark-68.clerk.accounts.dev/). Keep the
  // Auth0 additions for the return path.
  const scriptExtras = [auth0Origin, clerkOrigin].filter(Boolean).join(" ");

  const scriptSrc = isDev
    ? `script-src 'self' 'unsafe-inline' 'unsafe-eval' ${scriptExtras}`.trim()
    : `script-src 'self' 'unsafe-inline' ${scriptExtras}`.trim();

  response.headers.set(
    "Content-Security-Policy",
    [
      "default-src 'self'",
      scriptSrc,
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: https:",
      "font-src 'self'",
      `connect-src 'self' ${scriptExtras}`.trim(),
      "frame-ancestors 'none'",
      "base-uri 'self'",
      `form-action 'self' ${scriptExtras}`.trim(),
    ].join("; "),
  );

  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");

  return response;
}

const isProtectedRoute = createRouteMatcher([
  "/((?!sign-in|sign-up|login|api/auth|embed|demo|terms|privacy|landing|$).*)",
]);

// --- Clerk path --------------------------------------------------------
const clerkMw = clerkMiddleware(async (auth, request) => {
  const tenantDomain = resolveTenantDomain(request);
  if (isProtectedRoute(request)) {
    const { userId } = await auth();
    if (!userId) {
      const loginUrl = new URL("/sign-in", request.url);
      loginUrl.searchParams.set("redirect_url", request.url);
      return NextResponse.redirect(loginUrl);
    }
  }
  return applyCommonHeaders(NextResponse.next(), tenantDomain);
});

// --- Auth0 / NextAuth path --------------------------------------------
async function nextAuthMiddleware(request: NextRequest): Promise<NextResponse> {
  const { pathname } = request.nextUrl;
  const tenantDomain = resolveTenantDomain(request);

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

  return applyCommonHeaders(NextResponse.next(), tenantDomain);
}

// Single exported middleware — branches on the active provider so flipping
// NEXT_PUBLIC_AUTH_PROVIDER does not require swapping import paths.
export function middleware(request: NextRequest) {
  if (AUTH_PROVIDER === "clerk") {
    return clerkMw(request, {} as never);
  }
  return nextAuthMiddleware(request);
}

export const config = {
  matcher: "/((?!_next/static|_next/image|favicon.ico|.*\\.html$).*)",
};
