"use client";

import { SWRConfig } from "swr";
import { swrConfig } from "@/lib/swr-config";
import { FilterProvider } from "@/contexts/filter-context";
import { Suspense, type ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <SWRConfig value={swrConfig}>
      <Suspense>
        <FilterProvider>{children}</FilterProvider>
      </Suspense>
    </SWRConfig>
  );
}
