"use client";

/**
 * V2Layout — shared layout wrapper for every route that renders on the
 * v2 DashboardShell.
 *
 * Before this component existed, `/dashboard/layout.tsx` and
 * `/inventory/layout.tsx` each duplicated ~100 lines of identical provider
 * wiring + fonts + SessionGuard + floating NotificationBell. Every new
 * migrated page would copy the same boilerplate, which doesn't scale.
 *
 * V2Layout consolidates that wiring in one place. Each route-level
 * `layout.tsx` becomes a three-line file that just forwards children:
 *
 *     import V2Layout from "@/components/dashboard-v2/v2-layout";
 *     export default function FooLayout({ children }) {
 *       return <V2Layout>{children}</V2Layout>;
 *     }
 *
 * What lives here:
 *   - Fraunces + JetBrains Mono fonts (scoped via CSS variables)
 *   - Providers stack (SWR, Auth, Theme, Filters, Analytics, etc.)
 *   - ErrorBoundary / ToastProvider / BrandProvider
 *   - SessionGuard (blocks render until auth resolved; triggers signIn
 *     on refresh-token failure)
 *   - V2Shell (CommandPalette, OnboardingOverlay, KeyboardShortcutsHelp,
 *     floating NotificationBell, main#main-content for a11y)
 *
 * What does NOT live here:
 *   - The DashboardShell chrome itself (sidebar + pulse bar) — each
 *     page renders its own with page-specific activeHref + breadcrumbs.
 *   - The (app) route-group Sidebar — this is intentionally outside
 *     that group.
 */

import { useEffect, useState, type ReactNode } from "react";
import { useSession, signIn } from "next-auth/react";
import { Fraunces, JetBrains_Mono } from "next/font/google";

import { Providers } from "@/components/providers";
import { ErrorBoundary } from "@/components/error-boundary";
import { ToastProvider } from "@/components/ui/toast";
import { BrandProvider } from "@/components/branding/brand-provider";
import { CommandPalette } from "@/components/command-palette";
import { OnboardingOverlay } from "@/components/onboarding/onboarding-overlay";
import { NotificationBell } from "@/components/notifications/notification-bell";
import { NotificationCenter } from "@/components/notifications/notification-center";
import { KeyboardShortcutsHelp } from "@/components/keyboard-shortcuts-help";
import { useKeyboardShortcuts } from "@/hooks/use-keyboard-shortcuts";

const fraunces = Fraunces({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-fraunces",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

function SessionGuard({ children }: { children: ReactNode }) {
  const { data: session, status } = useSession();

  useEffect(() => {
    if ((session as { error?: string } | null)?.error === "RefreshAccessTokenError") {
      signIn("auth0");
    }
  }, [session]);

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-page">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      </div>
    );
  }

  return <>{children}</>;
}

function V2Shell({ children }: { children: ReactNode }) {
  const [notifOpen, setNotifOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  useKeyboardShortcuts(() => setShortcutsOpen(true));

  return (
    <>
      <CommandPalette />
      <OnboardingOverlay />
      <KeyboardShortcutsHelp open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
      <div className="fixed right-3 top-3.5 z-50 flex items-center gap-2 sm:right-4 sm:top-4 lg:right-6 lg:top-4">
        <div className="relative">
          <NotificationBell onClick={() => setNotifOpen(!notifOpen)} />
          <NotificationCenter open={notifOpen} onClose={() => setNotifOpen(false)} />
        </div>
      </div>
      <main id="main-content">{children}</main>
    </>
  );
}

export default function V2Layout({ children }: { children: ReactNode }) {
  return (
    <div className={`${fraunces.variable} ${jetbrainsMono.variable}`}>
      <Providers>
        <ErrorBoundary>
          <ToastProvider>
            <BrandProvider>
              <SessionGuard>
                <V2Shell>{children}</V2Shell>
              </SessionGuard>
            </BrandProvider>
          </ToastProvider>
        </ErrorBoundary>
      </Providers>
    </div>
  );
}
