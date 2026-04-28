"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { useSession, signIn } from "@/lib/auth-bridge";

/**
 * Block children until the POS user is authenticated; redirect anonymous
 * visitors to the IdP sign-in page, preserving the current pathname.
 *
 * POS desktop context: the embedded Next.js server runs with
 * ``POS_DESKTOP_MODE=1`` which short-circuits ``middleware.ts`` (PR #692,
 * to avoid baking ``CLERK_SECRET_KEY`` into the installer). That leaves
 * the browser as the only auth gate.
 *
 * Audit C3 (2026-04-26): the previous guard had no ``unauthenticated``
 * branch — anonymous users reached ``/terminal`` →
 * ``<ShiftOpenModal>`` → ``postAPI(...)`` with no ``Authorization``
 * header, and the backend returned ``401 Authentication required``,
 * surfaced as a red error banner on the shift-open modal (incident
 * 2026-04-24). This component now actively triggers ``signIn()`` on the
 * unauthenticated state and refuses to render children, closing the gap.
 */
export function PosSessionGuard({ children }: { children: ReactNode }) {
  const { data: session, status } = useSession();
  const pathname = usePathname();
  const callbackUrl = pathname || "/terminal";

  useEffect(() => {
    // RefreshAccessTokenError can land on an "authenticated" status with
    // a stale token — same remediation as unauthenticated.
    const sessionError = (session as { error?: string } | null)?.error;
    if (status === "unauthenticated" || sessionError === "RefreshAccessTokenError") {
      void signIn(undefined, { callbackUrl });
    }
  }, [status, session, callbackUrl]);

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div
          className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent"
          role="status"
          aria-label="Loading session"
        />
      </div>
    );
  }

  // Refuse to render the POS surface for unauthenticated users — the
  // sign-in redirect is fired from the effect above. Rendering children
  // here is what allowed the unauthenticated terminal to call backend
  // APIs without a token (audit C3).
  if (status === "unauthenticated") {
    return null;
  }

  return <>{children}</>;
}
