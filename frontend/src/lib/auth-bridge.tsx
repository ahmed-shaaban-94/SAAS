/**
 * Provider-agnostic auth shim.
 *
 * Presents the NextAuth ``next-auth/react`` API (useSession, signIn, signOut,
 * getSession, SessionProvider) backed by whichever provider
 * ``NEXT_PUBLIC_AUTH_PROVIDER`` selects:
 *
 * - ``clerk`` (current): wraps ``@clerk/nextjs`` so the dashboard works
 *   while we migrate the SaaS plan off Auth0 for small clients.
 * - ``auth0`` (default / return path): delegates to NextAuth's
 *   ``next-auth/react`` — matching the original behaviour when we swap back.
 *
 * Call sites import from ``@/lib/auth-bridge`` so the provider change is
 * invisible to components. Restoring Auth0 is a config flag flip; no call
 * site needs to change.
 */

"use client";

import { ClerkProvider, useAuth, useClerk, useUser } from "@clerk/nextjs";
import NextAuth, {
  SessionProvider as NASessionProvider,
  getSession as naGetSession,
  signIn as naSignIn,
  signOut as naSignOut,
  useSession as naUseSession,
} from "next-auth/react";
import * as React from "react";

/** Which auth provider is active in this deployment. */
export type AuthProvider = "auth0" | "clerk";

export const AUTH_PROVIDER: AuthProvider =
  (process.env.NEXT_PUBLIC_AUTH_PROVIDER as AuthProvider) || "auth0";

const CLERK_JWT_TEMPLATE =
  process.env.NEXT_PUBLIC_CLERK_JWT_TEMPLATE || "datapulse";

/**
 * Fallback JWT templates tried when the primary template returns null or
 * throws (observed during the 2026-04-24 smoke run: the ``datapulse``
 * template intermittently returned ``No JWT template exists with name:
 * datapulse`` from Clerk's session-token endpoint even though the Backend
 * API + Dashboard both confirmed it existed).
 *
 * Order matters: first token that resolves to a non-null JWT wins.
 * All listed templates must emit ``tenant_id`` + ``roles`` claims
 * (backend ``core/auth.py`` reads them in that order).
 *
 * The literal default here (``datapulse-pos``) is a sibling template that
 * was already provisioned on the Clerk instance as a manual workaround.
 * Set ``NEXT_PUBLIC_CLERK_JWT_FALLBACK_TEMPLATES`` (comma-separated) to
 * override per deployment.
 */
const CLERK_JWT_FALLBACK_TEMPLATES: readonly string[] = (
  process.env.NEXT_PUBLIC_CLERK_JWT_FALLBACK_TEMPLATES || "datapulse-pos"
)
  .split(",")
  .map((s) => s.trim())
  .filter((s) => s && s !== CLERK_JWT_TEMPLATE);

/**
 * Most recent Clerk ``getToken`` failure, exposed to the rest of the app.
 *
 * ``getSession`` used to silently ``catch → return null``, which meant
 * ``api-client.ts`` would fire requests with no ``Authorization`` header
 * and the backend would respond ``401 Authentication required`` — giving
 * no clue *why* the token was missing. Now we stash the underlying reason
 * so ``api-client.ts`` can surface it in the thrown ``ApiError`` and pilots
 * see actionable text in the UI instead of a generic 401.
 *
 * Also mirrored onto ``window.__clerkAuthError`` for DevTools inspection.
 */
let _lastClerkAuthError: string | null = null;

export function getLastClerkAuthError(): string | null {
  return _lastClerkAuthError;
}

function recordClerkAuthError(reason: string, err?: unknown): void {
  const detail = err instanceof Error ? `${reason}: ${err.message}` : reason;
  _lastClerkAuthError = detail;
  // eslint-disable-next-line no-console
  console.error("[auth-bridge] Clerk token fetch failed —", detail, err);
  if (typeof window !== "undefined") {
    (window as unknown as { __clerkAuthError?: string }).__clerkAuthError = detail;
  }
}

function clearClerkAuthError(): void {
  _lastClerkAuthError = null;
  if (typeof window !== "undefined") {
    (window as unknown as { __clerkAuthError?: string }).__clerkAuthError = undefined;
  }
}

/** Shape of either source of Clerk's token fetcher — ``useAuth().getToken``
 *  (React hook) or ``window.Clerk.session.getToken`` (global). Both accept
 *  the same options object. */
type ClerkGetToken = (opts?: { template?: string }) => Promise<string | null>;

/**
 * Walk the template cascade (primary → fallbacks → no-template default) and
 * return the first non-null token. Records the reason-of-last-resort on
 * exhaustion so the UI can surface it.
 *
 * The ``source`` string (e.g. ``"useAuth"`` / ``"window.Clerk.session"``) is
 * only used to make the error log tell us which call path broke — the
 * behaviour is identical either way.
 */
async function getClerkTokenWithFallback(
  getToken: ClerkGetToken,
  source: string,
): Promise<string | null> {
  const candidates = [CLERK_JWT_TEMPLATE, ...CLERK_JWT_FALLBACK_TEMPLATES];
  const failures: string[] = [];
  for (const template of candidates) {
    try {
      const t = await getToken({ template });
      if (t) {
        if (failures.length > 0) {
          // eslint-disable-next-line no-console
          console.warn(
            `[auth-bridge] (${source}) primary template(s) ${failures
              .map((f) => `"${f.split("|")[0]}"`)
              .join(", ")} failed — using fallback template "${template}".`,
          );
        }
        clearClerkAuthError();
        return t;
      }
      failures.push(`${template}|null token`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      failures.push(`${template}|${msg}`);
    }
  }

  // Last-resort: fetch the *default* session token (no template). Backend
  // will reject it with "JWT missing tenant context" rather than
  // "Authentication required" — worse claims, but a different 4xx that
  // tells us Clerk issuance itself is not the blocker.
  try {
    const t = await getToken();
    if (t) {
      // eslint-disable-next-line no-console
      console.warn(
        `[auth-bridge] (${source}) every templated token failed — falling back to default session token. Backend will likely reject for missing tenant context.`,
      );
      recordClerkAuthError(
        `All JWT templates failed via ${source}: ${failures.join("; ")}. ` +
          `Falling back to default session token — backend will reject for missing tenant_id.`,
      );
      return t;
    }
  } catch {
    // fallthrough
  }

  recordClerkAuthError(
    `All Clerk token fetchers failed via ${source}: ${failures.join("; ")}`,
  );
  return null;
}

// ----------------------------------------------------------------------
// Session shape (matches NextAuth's Session for call-site compatibility)
// ----------------------------------------------------------------------

export interface AuthSessionUser {
  id?: string;
  name?: string | null;
  email?: string | null;
  image?: string | null;
  /** Added in core/auth.py — required for tenant-scoped RLS queries. */
  tenant_id?: string | number;
  /** Role list from the JWT (Auth0) or Clerk publicMetadata.roles. */
  roles?: string[];
}

export interface AuthSession {
  user: AuthSessionUser;
  /** Short-lived JWT for Authorization: Bearer calls to the backend. */
  accessToken?: string | null;
  expires: string;
}

export type AuthStatus = "authenticated" | "unauthenticated" | "loading";

export interface UseSessionReturn {
  data: AuthSession | null;
  status: AuthStatus;
  /** NextAuth exposes this via the "update" callback; Clerk bridge leaves it
   *  as a noop so the signature matches. */
  update: (...args: unknown[]) => Promise<AuthSession | null>;
}

// ----------------------------------------------------------------------
// Provider component — mounts ClerkProvider or NextAuth's SessionProvider
// ----------------------------------------------------------------------

export function SessionProvider({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  if (AUTH_PROVIDER === "clerk") {
    return <ClerkProvider>{children}</ClerkProvider>;
  }
  return <NASessionProvider>{children}</NASessionProvider>;
}

// ----------------------------------------------------------------------
// Hooks + helpers
// ----------------------------------------------------------------------

function clerkToBridgeSession(
  user: ReturnType<typeof useUser>["user"],
  token: string | null,
): AuthSession | null {
  if (!user) return null;
  const meta = (user.publicMetadata || {}) as Record<string, unknown>;
  const primaryEmail =
    user.primaryEmailAddress?.emailAddress ||
    user.emailAddresses?.[0]?.emailAddress ||
    null;
  return {
    user: {
      id: user.id,
      name: user.fullName ?? user.username ?? primaryEmail,
      email: primaryEmail,
      image: user.imageUrl,
      tenant_id: (meta.tenant_id as string | number | undefined) ?? "1",
      roles: (meta.roles as string[] | undefined) ?? [],
    },
    accessToken: token,
    // Clerk tokens live 60s by default; match NextAuth's shape with a
    // short-ish expiry so any stale-session logic behaves.
    expires: new Date(Date.now() + 60 * 1000).toISOString(),
  };
}

/**
 * Clerk implementation of useSession. Mirrors NextAuth's return shape so
 * existing call sites compile and behave unchanged.
 *
 * Token fetching uses the configured JWT template (default: ``datapulse``)
 * so backend JWT verification reads the same claim shape as Auth0 tokens.
 */
function useClerkSession(): UseSessionReturn {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const { user } = useUser();
  const [token, setToken] = React.useState<string | null>(null);

  // Fetch the backend JWT once the user is signed in. Refresh lazily —
  // Clerk's SDK handles rotation; we refetch when the component re-renders
  // (SWR/useSession callers typically do on navigation).
  React.useEffect(() => {
    let cancelled = false;
    async function pull() {
      if (!isSignedIn) {
        if (!cancelled) setToken(null);
        clearClerkAuthError();
        return;
      }
      const t = await getClerkTokenWithFallback(
        getToken as ClerkGetToken,
        "useAuth",
      );
      if (!cancelled) setToken(t);
    }
    pull();
    return () => {
      cancelled = true;
    };
  }, [isSignedIn, getToken]);

  const status: AuthStatus = !isLoaded
    ? "loading"
    : isSignedIn
      ? "authenticated"
      : "unauthenticated";

  const data = clerkToBridgeSession(user, token);

  return {
    data: status === "authenticated" ? data : null,
    status,
    update: async () => data,
  };
}

/** NextAuth useSession wrapper — returns the shape we expose. */
function useAuth0Session(): UseSessionReturn {
  return naUseSession() as unknown as UseSessionReturn;
}

/**
 * The active ``useSession`` is chosen once at module-init time so React
 * sees the same hook on every render (rules-of-hooks). Swapping providers
 * requires an env change + rebuild, not a runtime branch inside the hook.
 */
export const useSession: () => UseSessionReturn =
  AUTH_PROVIDER === "clerk" ? useClerkSession : useAuth0Session;

/**
 * Grab the current session outside a React render. Used by the shared fetch
 * wrapper in ``lib/api-client.ts`` to attach Authorization headers.
 *
 * For Clerk, this reads the session token from the Clerk JS global set up
 * by ClerkProvider. Returns null in non-browser contexts so SSR callers
 * behave identically to NextAuth's pre-hydration getSession().
 */
export async function getSession(): Promise<AuthSession | null> {
  if (AUTH_PROVIDER !== "clerk") {
    const ses = await naGetSession();
    return ses as unknown as AuthSession | null;
  }

  if (typeof window === "undefined") return null;

  const clerk = (window as unknown as { Clerk?: ClerkJSWindowShape }).Clerk;
  if (!clerk) {
    recordClerkAuthError(
      "window.Clerk is undefined — Clerk JS has not finished booting. " +
        "Verify NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY is inlined in the build.",
    );
    return null;
  }
  if (!clerk.session) {
    recordClerkAuthError("window.Clerk.session is null — user is not signed in.");
    return null;
  }
  if (!clerk.user) {
    recordClerkAuthError("window.Clerk.user is null — session missing user context.");
    return null;
  }

  try {
    const token = await getClerkTokenWithFallback(
      clerk.session.getToken.bind(clerk.session) as ClerkGetToken,
      "window.Clerk.session",
    );
    return clerkToBridgeSession(clerk.user as never, token ?? null);
  } catch (err) {
    recordClerkAuthError(
      `window.Clerk.session.getToken cascade threw unexpectedly`,
      err,
    );
    return null;
  }
}

interface ClerkJSWindowShape {
  session?: { getToken: (opts: { template: string }) => Promise<string | null> };
  user?: unknown;
  signOut?: () => Promise<void>;
  redirectToSignIn?: (opts?: { redirectUrl?: string }) => void;
}

// ----------------------------------------------------------------------
// signIn / signOut shims
// ----------------------------------------------------------------------

export interface SignInOptions {
  callbackUrl?: string;
  redirect?: boolean;
  [key: string]: unknown;
}

/**
 * Kick off sign-in. For Clerk this navigates to ``/sign-in`` (the hosted
 * route Clerk's SignIn component lives on). For Auth0 it defers to
 * NextAuth's signIn so OAuth PKCE still works.
 */
export async function signIn(
  providerId?: string | null,
  options?: SignInOptions,
): Promise<unknown> {
  if (AUTH_PROVIDER !== "clerk") {
    return naSignIn(providerId ?? undefined, options);
  }
  if (typeof window === "undefined") return null;
  const target = options?.callbackUrl || "/dashboard";
  const url = new URL("/sign-in", window.location.origin);
  url.searchParams.set("redirect_url", target);
  window.location.href = url.toString();
  return null;
}

/** End the session on the active provider. */
export async function signOut(options?: {
  callbackUrl?: string;
  redirect?: boolean;
}): Promise<unknown> {
  if (AUTH_PROVIDER !== "clerk") {
    return naSignOut(options);
  }
  if (typeof window === "undefined") return null;
  const clerk = (window as unknown as { Clerk?: ClerkJSWindowShape }).Clerk;
  if (clerk?.signOut) {
    await clerk.signOut();
  }
  if (options?.redirect !== false) {
    window.location.href = options?.callbackUrl || "/login";
  }
  return null;
}

/**
 * Clerk-specific escape hatch for call sites that need the raw hooks
 * (e.g. to render ``<UserButton>`` or surface Clerk-only UX). The rest of
 * the app should use the bridge, not these.
 */
export { useAuth as useClerkAuth, useClerk, useUser as useClerkUser };

// Re-export NextAuth for the narrow set of places that still hit it
// directly (e.g. legacy route handlers). New code should not use this.
export { NextAuth as _NextAuthLegacy };
