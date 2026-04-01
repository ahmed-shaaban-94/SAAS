"use client";

import { signIn } from "next-auth/react";
import { useSearchParams } from "next/navigation";
import { Activity, LogIn } from "lucide-react";
import { Suspense } from "react";

function LoginForm() {
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") || "/dashboard";
  const error = searchParams.get("error");

  return (
    <div className="flex min-h-screen items-center justify-center bg-page px-4">
      <div className="w-full max-w-sm space-y-8">
        {/* Logo */}
        <div className="flex flex-col items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-accent/10">
            <Activity className="h-8 w-8 text-accent" />
          </div>
          <h1 className="text-2xl font-bold text-text-primary">DataPulse</h1>
          <p className="text-sm text-text-secondary">
            Sales Analytics Platform
          </p>
        </div>

        {/* Card */}
        <div className="rounded-xl border border-border bg-card p-8 shadow-lg">
          <h2 className="mb-2 text-center text-lg font-semibold text-text-primary">
            Welcome back
          </h2>
          <p className="mb-6 text-center text-sm text-text-secondary">
            Sign in to access your dashboards
          </p>

          {error && (
            <div className="mb-4 rounded-lg border border-growth-red/30 bg-growth-red/10 px-4 py-3 text-sm text-growth-red">
              {error === "OAuthSignin" && "Could not start sign-in flow."}
              {error === "OAuthCallback" && "Authentication callback failed."}
              {error === "SessionRequired" && "Please sign in to continue."}
              {!["OAuthSignin", "OAuthCallback", "SessionRequired"].includes(error) &&
                "An authentication error occurred."}
            </div>
          )}

          <button
            onClick={() => signIn("auth0", { callbackUrl })}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-4 py-3 text-sm font-medium text-page transition-colors hover:bg-accent/90 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-page"
          >
            <LogIn className="h-4 w-4" />
            Sign In
          </button>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-text-secondary">
          Secured by Keycloak OIDC
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-page">
          <Activity className="h-8 w-8 animate-pulse text-accent" />
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
