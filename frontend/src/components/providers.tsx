"use client";

import { SWRConfig, useSWRConfig } from "swr";
import { swrConfig, setApiErrorCallback } from "@/lib/swr-config";
import { FilterProvider } from "@/contexts/filter-context";
import { AuthProvider } from "@/components/auth-provider";
import { ThemeProvider } from "next-themes";
import { Suspense, useEffect, type ReactNode } from "react";
import { AnalyticsProvider } from "@/components/analytics-provider";
import { WebVitals } from "@/components/web-vitals";
import { ApiStatusBanner } from "@/components/api-status-banner";
import { useApiHealth } from "@/hooks/use-api-health";

function ApiHealthGate({ children }: { children: ReactNode }) {
  const { mutate } = useSWRConfig();
  const { isApiDown, isRecovering, reportError } = useApiHealth(() => {
    // On recovery, revalidate ALL cached SWR keys so stale data refreshes
    mutate(() => true);
  });

  // Wire SWR global error handler to the health monitor
  useEffect(() => {
    setApiErrorCallback(reportError);
  }, [reportError]);

  return (
    <>
      <ApiStatusBanner isApiDown={isApiDown} isRecovering={isRecovering} />
      {children}
    </>
  );
}

export function Providers({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <AnalyticsProvider>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
          <SWRConfig value={swrConfig}>
            <WebVitals />
            <ApiHealthGate>
              <Suspense fallback={<div className="min-h-screen bg-background" />}>
                <FilterProvider>{children}</FilterProvider>
              </Suspense>
            </ApiHealthGate>
          </SWRConfig>
        </ThemeProvider>
      </AnalyticsProvider>
    </AuthProvider>
  );
}
