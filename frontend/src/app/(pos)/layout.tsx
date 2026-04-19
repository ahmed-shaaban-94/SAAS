"use client";

import { useEffect, useCallback, type ReactNode } from "react";
import { useSession, signIn } from "next-auth/react";
import { ThemeProvider } from "next-themes";
import { SWRConfig } from "swr";
import { swrConfig } from "@/lib/swr-config";
import { AuthProvider } from "@/components/auth-provider";
import { ErrorBoundary } from "@/components/error-boundary";
import { ToastProvider } from "@/components/ui/toast";
import { PosCartProvider } from "@/contexts/pos-cart-context";
import { PosShellTopBar } from "@/components/pos/shell/PosShellTopBar";

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

/** Keyboard shortcuts for the POS terminal */
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
      case "F12":
        e.preventDefault();
        window.dispatchEvent(new CustomEvent("pos:void-transaction"));
        break;
    }
  }, []);

  useEffect(() => {
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [handleKey]);

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
                  <PosKeyboardHandler>
                    <div className="pos-root flex min-h-screen flex-col overflow-hidden bg-background text-foreground">
                      <PosShellTopBar />
                      <main className="flex-1 overflow-auto">{children}</main>
                    </div>
                  </PosKeyboardHandler>
                </PosCartProvider>
              </SessionGuard>
            </ToastProvider>
          </ErrorBoundary>
        </SWRConfig>
      </AuthProvider>
    </ThemeProvider>
  );
}
