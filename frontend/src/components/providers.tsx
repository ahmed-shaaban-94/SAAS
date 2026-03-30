"use client";

import { SWRConfig } from "swr";
import { swrConfig } from "@/lib/swr-config";
import { FilterProvider } from "@/contexts/filter-context";
import { AuthProvider } from "@/components/auth-provider";
import { ThemeProvider } from "next-themes";
import { Suspense, type ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
        <SWRConfig value={swrConfig}>
          <Suspense fallback={<div className="min-h-screen bg-background" />}>
            <FilterProvider>{children}</FilterProvider>
          </Suspense>
        </SWRConfig>
      </ThemeProvider>
    </AuthProvider>
  );
}
