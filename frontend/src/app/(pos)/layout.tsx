"use client";

import { useEffect, useCallback, type ReactNode } from "react";
import { Fraunces, JetBrains_Mono, Cairo } from "next/font/google";
import { useSession, signIn } from "@/lib/auth-bridge";
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

function SessionGuard({ children }: { children: ReactNode }) {
  const { data: session, status } = useSession();

  useEffect(() => {
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
    if (status === "unauthenticated" && isPosDesktopRuntime()) {
      void signIn(undefined, { callbackUrl: "/terminal" });
    }
  }, [status, session]);

  // Block rendering only during the initial loading phase — matches the
  // (app) layout pattern. Unauthenticated renders fall through to children;
  // the middleware redirect handles unauthenticated web-app access, and
  // E2E CI tests need `main` to be reachable before session is confirmed.
  if (status === "loading") {
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
