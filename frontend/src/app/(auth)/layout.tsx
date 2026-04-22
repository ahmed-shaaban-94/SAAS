/**
 * Layout for auth pages (/sign-in, /sign-up, /login redirect).
 *
 * Mounts the minimum providers Clerk's `<SignIn>` / `<SignUp>` components
 * need: the auth bridge (which wraps them in ClerkProvider when
 * NEXT_PUBLIC_AUTH_PROVIDER=clerk) and the theme provider (so
 * ``useTheme()`` inside those pages returns the right dark/light token
 * set). We intentionally do NOT mount the full `<Providers>` stack here
 * because SWR, analytics, and ApiHealthGate add no value on a login
 * page — just cost.
 */

import { ThemeProvider } from "next-themes";
import { AuthProvider } from "@/components/auth-provider";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthProvider>
      <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
        {children}
      </ThemeProvider>
    </AuthProvider>
  );
}
