"use client";

import { Sidebar } from "@/components/layout/sidebar";
import { Providers } from "@/components/providers";
import { ErrorBoundary } from "@/components/error-boundary";
import { ToastProvider } from "@/components/ui/toast";
import { useAIAnomalies } from "@/hooks/use-ai-anomalies";

function AppShell({ children }: { children: React.ReactNode }) {
  const { data } = useAIAnomalies();
  const anomalyCount = data?.anomalies?.length ?? 0;

  return (
    <>
      <Sidebar anomalyCount={anomalyCount} />
      <main id="main-content" className="min-h-screen p-4 pt-18 lg:ml-60 lg:p-6 lg:pt-6">
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
