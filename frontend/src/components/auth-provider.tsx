"use client";

import { SessionProvider } from "@/lib/auth-bridge";
import type { ReactNode } from "react";

/**
 * Thin wrapper around the auth-bridge SessionProvider. At runtime it resolves
 * to either ClerkProvider (NEXT_PUBLIC_AUTH_PROVIDER=clerk) or NextAuth's
 * SessionProvider — keeping the auth swap transparent to app/layout.tsx.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  return <SessionProvider>{children}</SessionProvider>;
}
