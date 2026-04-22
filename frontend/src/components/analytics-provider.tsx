"use client";

import { useEffect } from "react";
import { useSession } from "@/lib/auth-bridge";
import { initAnalytics, identifyUser } from "@/lib/analytics";

/**
 * Initializes PostHog on mount and identifies the authenticated user.
 * Renders nothing — purely a side-effect provider.
 */
export function AnalyticsProvider({ children }: { children: React.ReactNode }) {
  const { data: session } = useSession();

  useEffect(() => {
    initAnalytics();
  }, []);

  useEffect(() => {
    if (session?.user?.email) {
      identifyUser(session.user.email, {
        name: session.user.name ?? undefined,
      });
    }
  }, [session]);

  return <>{children}</>;
}
