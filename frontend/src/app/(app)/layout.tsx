"use client";

import { Sidebar } from "@/components/layout/sidebar";
import { Providers } from "@/components/providers";
import { ErrorBoundary } from "@/components/error-boundary";
import { ToastProvider } from "@/components/ui/toast";
import { useAIAnomalies } from "@/hooks/use-ai-anomalies";
import { useAlertLog } from "@/hooks/use-alerts";

function AppShell({ children }: { children: React.ReactNode }) {
  const { data } = useAIAnomalies();
  const anomalyCount = data?.anomalies?.length ?? 0;
  const { data: alerts } = useAlertLog(true);
  const alertCount = alerts?.length ?? 0;

  return (
    <>
      <div className="ambient-bg" aria-hidden="true" />
      <Sidebar anomalyCount={anomalyCount} alertCount={alertCount} />
      <main id="main-content" className="min-h-screen p-4 pt-16 lg:ml-60 lg:p-6 lg:pt-6">
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
