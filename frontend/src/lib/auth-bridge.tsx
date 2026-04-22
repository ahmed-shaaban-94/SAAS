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
        return;
      }
      try {
        const t = await getToken({ template: CLERK_JWT_TEMPLATE });
        if (!cancelled) setToken(t ?? null);
      } catch {
        if (!cancelled) setToken(null);
      }
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
  if (!clerk?.session || !clerk.user) return null;

  try {
    const token = await clerk.session.getToken({ template: CLERK_JWT_TEMPLATE });
    return clerkToBridgeSession(clerk.user as never, token ?? null);
  } catch {
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
