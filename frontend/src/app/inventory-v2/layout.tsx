"use client";

/**
 * /inventory-v2 layout — mirrors /dashboard/layout.tsx.
 *
 * Real inventory widgets (InventoryOverview, StockLevelTable, etc.) depend
 * on the full app provider stack: FilterProvider (date filters drive the
 * queries), SWRConfig (data fetching), AuthProvider/SessionGuard (auth),
 * BrandProvider (theming), ToastProvider (error surfacing). Without these,
 * the page throws during hydration and never renders h1.page-title.
 *
 * This route is a preview; once /inventory migrates in place, delete the
 * entire inventory-v2 folder.
 */

import { useEffect, useState } from "react";
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

function SessionGuard({ children }: { children: React.ReactNode }) {
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

function V2Shell({ children }: { children: React.ReactNode }) {
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

export default function InventoryV2Layout({
  children,
}: {
  children: React.ReactNode;
}) {
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
