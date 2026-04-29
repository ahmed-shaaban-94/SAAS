"use client";

import { useEffect, useCallback, useRef, useState, type ReactNode } from "react";
import { Fraunces, JetBrains_Mono, Cairo } from "next/font/google";
import { useSession, signIn, AUTH_PROVIDER, CLERK_KEY_CONFIGURED } from "@/lib/auth-bridge";
import { ThemeProvider } from "next-themes";
import { SWRConfig } from "swr";
import { swrConfig } from "@/lib/swr-config";
import { AuthProvider } from "@/components/auth-provider";
import { ErrorBoundary } from "@/components/error-boundary";
import { ToastProvider } from "@/components/ui/toast";
import { PosCartProvider } from "@/contexts/pos-cart-context";
import { useRendererCrashBridge } from "@/hooks/use-renderer-crash-bridge";
import { BrandProvider } from "@/components/branding/brand-provider";

// Fraunces = italic display on the Totals Hero + invoice.
// JetBrains Mono = SKUs, barcodes, numeric readouts, kbd chips.
const fraunces = Fraunces({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  style: ["italic", "normal"],
  variable: "--font-fraunces",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

// Arabic body copy on the POS + receipt surfaces. Cairo fills the
// --font-plex-arabic slot — see PR #620 for why we swapped off
// IBM_Plex_Sans_Arabic (squash-merge dropped the import + next 15.5.15
// SWC name-resolution failure) and why Cairo is the right substitute
// (DataPulse's own colors_and_type.css names Cairo as `--dp-font-ar`).
const plexArabic = Cairo({
  subsets: ["arabic"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-plex-arabic",
  display: "swap",
});

/** Block children until the user is authenticated; redirect anonymous
 *  visitors to the IdP sign-in page.
 *
 *  POS desktop context: the embedded Next.js server runs with
 *  ``POS_DESKTOP_MODE=1`` which short-circuits ``middleware.ts`` (#692,
 *  to avoid baking ``CLERK_SECRET_KEY`` into the installer). That leaves
 *  the browser as the only auth gate. Without this guard, anonymous
 *  users reach ``/terminal`` → ``<ShiftOpenModal>`` → ``postAPI(...)``
 *  with no ``Authorization`` header, and the backend responds
 *  ``401 Authentication required`` — surfaced as a red error banner on
 *  the shift-open modal (incident 2026-04-24).
 */
/** Detect whether we're running inside the Electron POS shell.
 *
 *  In the SaaS web build, ``middleware.ts`` redirects unauthenticated users
 *  before they reach the layout. In the Electron POS desktop shell that
 *  middleware is short-circuited (``POS_DESKTOP_MODE=1`` — see #692) so
 *  the only available auth gate is the browser. We use the presence of
 *  ``window.electronAPI`` as the runtime signal — same idiom used by
 *  ``use-renderer-crash-bridge`` to detect Electron mounts.
 */
function isPosDesktopRuntime(): boolean {
  if (typeof window === "undefined") return false;
  return Boolean((window as unknown as { electronAPI?: unknown }).electronAPI);
}

// How long to wait for Clerk to initialize before giving up in the desktop
// shell. Clerk needs internet to boot; if offline or the origin is blocked,
// isLoaded never fires. 8 s covers slow connections without blocking cashiers.
const CLERK_LOAD_TIMEOUT_MS = 8_000;

function isClerkAuthMissing(): boolean {
  return AUTH_PROVIDER === "clerk" && !CLERK_KEY_CONFIGURED;
}

function SessionGuard({ children }: { children: ReactNode }) {
  const { data: session, status } = useSession();
  const isDesktop = isPosDesktopRuntime();
  const clerkAuthMissing = isClerkAuthMissing();

  // Track whether the Clerk load timeout has fired. Once it fires we stop
  // blocking the render — the terminal renders and the offline-grant path
  // in ShiftOpenModal handles authentication from the SQLite store.
  const [clerkTimedOut, setClerkTimedOut] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    // Only arm the timeout in the Electron desktop shell — the web build
    // always has internet, so Clerk loads promptly and the timer is wasted.
    if (!isDesktop || status !== "loading") return;
    if (timerRef.current) return; // already armed
    timerRef.current = setTimeout(() => setClerkTimedOut(true), CLERK_LOAD_TIMEOUT_MS);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [isDesktop, status]);

  // Cancel the timeout as soon as Clerk resolves (online path).
  useEffect(() => {
    if (status !== "loading" && timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
      setClerkTimedOut(false);
    }
  }, [status]);

  useEffect(() => {
    // No-op when Clerk was not configured — the render branch below handles it.
    if (clerkAuthMissing) return;
    // Refresh-token errors always need a re-auth, regardless of runtime.
    if ((session as { error?: string } | null)?.error === "RefreshAccessTokenError") {
      void signIn(undefined, { callbackUrl: "/terminal" });
      return;
    }
    // Audit C3 (2026-04-26): in the Electron POS shell middleware is
    // bypassed, so unauthenticated visitors must be pushed to sign-in
    // here — otherwise the terminal mounts, hits the API, and surfaces a
    // 401 banner instead of a sign-in flow. The web build keeps the
    // fall-through so middleware owns the redirect (E2E CI relies on it).
    if (status === "unauthenticated" && isDesktop) {
      void signIn(undefined, { callbackUrl: "/terminal" });
    }
  }, [status, session, isDesktop, clerkAuthMissing]);

  // When Clerk was not configured at build time, show a build-config error.
  // Catches CI smoke builds (PR/branch without the secret) before they
  // redirect to a /sign-in page that would be equally broken. Stable across
  // SSR and hydration — no window access, so no mismatch.
  if (clerkAuthMissing) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background p-8 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-8 w-8 text-destructive"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
            />
          </svg>
        </div>
        <h1 className="text-lg font-semibold text-text-primary">Authentication not configured</h1>
        <p className="max-w-sm text-sm text-text-secondary">
          This installer was built without a Clerk publishable key and cannot
          authenticate. Use a tagged release{" "}
          <span className="font-mono text-xs">pos-desktop-v*.*.*</span> or add{" "}
          <span className="font-mono text-xs">NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY</span>{" "}
          to GitHub Actions secrets.
        </p>
      </div>
    );
  }

  // Block rendering only during the initial loading phase.
  // Exception: in the desktop shell, if Clerk has not resolved within
  // CLERK_LOAD_TIMEOUT_MS (no internet / origin blocked), stop blocking and
  // let the terminal render — ShiftOpenModal's offline-grant path takes over.
  if (status === "loading" && !clerkTimedOut) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      </div>
    );
  }

  return <>{children}</>;
}

/** Keyboard shortcuts for the POS terminal.
 *
 * Audit C-follow-up: removed the F12 dispatch here — it fired
 * ``pos:void-transaction`` which no component listened to, AND it collided
 * with the terminal page's own F12 handler (voucher modal) because both
 * handlers attach to window.keydown. Net effect was a dead event plus a
 * preventDefault race. F12 is now owned by the terminal page alone
 * (voucher) until product decides whether to rebind it to void to match
 * the pharma-pos skill convention.
 */
function PosKeyboardHandler({ children }: { children: ReactNode }) {
  const handleKey = useCallback((e: KeyboardEvent) => {
    // Dispatch custom events so any component can listen without prop-drilling
    switch (e.key) {
      case "F1":
        e.preventDefault();
        window.dispatchEvent(new CustomEvent("pos:focus-search"));
        break;
      case "F2":
        e.preventDefault();
        window.dispatchEvent(new CustomEvent("pos:open-checkout"));
        break;
      case "F5":
        e.preventDefault();
        window.dispatchEvent(new CustomEvent("pos:hold-transaction"));
        break;
      case "F8":
        e.preventDefault();
        window.dispatchEvent(new CustomEvent("pos:open-return"));
        break;
    }
  }, []);

  useEffect(() => {
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [handleKey]);

  return <>{children}</>;
}

/** POS-only mount of the renderer-error bridge. Self-contained so it
 *  can be removed without touching the layout tree. Runs only inside
 *  Electron (the hook no-ops when `window.electronAPI` is undefined). */
function RendererCrashBridge({ children }: { children: ReactNode }) {
  useRendererCrashBridge();
  return <>{children}</>;
}

export default function PosLayout({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
      <AuthProvider>
        <SWRConfig value={swrConfig}>
          <ErrorBoundary>
            <ToastProvider>
              <SessionGuard>
                <BrandProvider>
                <PosCartProvider>
                  <RendererCrashBridge>
                    <PosKeyboardHandler>
                      <div
                        className={`pos-omni ${fraunces.variable} ${jetbrainsMono.variable} ${plexArabic.variable} flex min-h-screen flex-col overflow-hidden bg-[var(--pos-bg)] text-[var(--pos-ink)]`}
                      >
                        {children}
                      </div>
                    </PosKeyboardHandler>
                  </RendererCrashBridge>
                </PosCartProvider>
                </BrandProvider>
              </SessionGuard>
            </ToastProvider>
          </ErrorBoundary>
        </SWRConfig>
      </AuthProvider>
    </ThemeProvider>
  );
}
