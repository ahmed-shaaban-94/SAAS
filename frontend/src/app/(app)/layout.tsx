"use client";

import { useState } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Providers } from "@/components/providers";
import { ErrorBoundary } from "@/components/error-boundary";
import { ToastProvider } from "@/components/ui/toast";
import { CommandPalette } from "@/components/command-palette";
import { OnboardingOverlay } from "@/components/onboarding/onboarding-overlay";
import { NotificationBell } from "@/components/notifications/notification-bell";
import { NotificationCenter } from "@/components/notifications/notification-center";
import { KeyboardShortcutsHelp } from "@/components/keyboard-shortcuts-help";
import { useKeyboardShortcuts } from "@/hooks/use-keyboard-shortcuts";
import { useAIAnomalies } from "@/hooks/use-ai-anomalies";
import { useAlertLog } from "@/hooks/use-alerts";

function AppShell({ children }: { children: React.ReactNode }) {
  const [notifOpen, setNotifOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  useKeyboardShortcuts(() => setShortcutsOpen(true));
  const { data } = useAIAnomalies();
  const anomalyCount = data?.anomalies?.length ?? 0;
  const { data: alerts } = useAlertLog(true);
  const alertCount = alerts?.length ?? 0;

  return (
    <>
      <div className="ambient-bg" aria-hidden="true" />
      <Sidebar anomalyCount={anomalyCount} alertCount={alertCount} />
      <CommandPalette />
      <OnboardingOverlay />
      <KeyboardShortcutsHelp open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
      <main id="main-content" className="min-h-screen p-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] pt-14 sm:p-4 sm:pt-16 lg:ml-60 lg:p-6 lg:pt-6">
        {/* Header actions */}
        <div className="fixed right-3 top-3.5 z-40 flex items-center gap-2 sm:right-4 sm:top-4 lg:right-6 lg:top-4">
          <div className="relative">
            <NotificationBell onClick={() => setNotifOpen(!notifOpen)} />
            <NotificationCenter open={notifOpen} onClose={() => setNotifOpen(false)} />
          </div>
        </div>
        {children}
      </main>
    </>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <Providers>
      <ErrorBoundary>
        <ToastProvider>
          <AppShell>{children}</AppShell>
        </ToastProvider>
      </ErrorBoundary>
    </Providers>
  );
}
