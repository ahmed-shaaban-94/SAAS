"use client";

import { useEffect, useCallback, type ReactNode } from "react";
import { Fraunces, JetBrains_Mono } from "next/font/google";
import { useSession, signIn } from "next-auth/react";
import { ThemeProvider } from "next-themes";
import { SWRConfig } from "swr";
import { swrConfig } from "@/lib/swr-config";
import { AuthProvider } from "@/components/auth-provider";
import { ErrorBoundary } from "@/components/error-boundary";
import { ToastProvider } from "@/components/ui/toast";
import { PosCartProvider } from "@/contexts/pos-cart-context";
import { useRendererCrashBridge } from "@/hooks/use-renderer-crash-bridge";

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

/** Block children until session is resolved; redirect on refresh failure. */
function SessionGuard({ children }: { children: ReactNode }) {
  const { data: session, status } = useSession();

  useEffect(() => {
    if ((session as { error?: string } | null)?.error === "RefreshAccessTokenError") {
      signIn("auth0");
    }
  }, [session]);

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
                <PosCartProvider>
                  <RendererCrashBridge>
                    <PosKeyboardHandler>
                      <div
                        className={`${fraunces.variable} ${jetbrainsMono.variable} flex min-h-screen flex-col overflow-hidden bg-background text-foreground`}
                      >
                        {children}
                      </div>
                    </PosKeyboardHandler>
                  </RendererCrashBridge>
                </PosCartProvider>
              </SessionGuard>
            </ToastProvider>
          </ErrorBoundary>
        </SWRConfig>
      </AuthProvider>
    </ThemeProvider>
  );
}
