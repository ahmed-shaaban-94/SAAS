import { SignIn } from "@clerk/nextjs";
import { Activity } from "lucide-react";

/**
 * Clerk hosted sign-in.
 *
 * Active when ``NEXT_PUBLIC_AUTH_PROVIDER=clerk``. The NextAuth login page
 * at ``/login`` still exists for the return-to-Auth0 path; the middleware
 * redirects to whichever one matches the active provider.
 */
export default function SignInPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-page px-4">
      <div className="w-full max-w-sm space-y-8">
        <div className="flex flex-col items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-accent/10">
            <Activity className="h-8 w-8 text-accent" />
          </div>
          <h1 className="text-2xl font-bold text-text-primary">DataPulse</h1>
          <p className="text-sm text-text-secondary">Sales Analytics Platform</p>
        </div>
        <SignIn
          routing="path"
          path="/sign-in"
          signUpUrl="/sign-up"
          fallbackRedirectUrl="/dashboard"
        />
        <p className="text-center text-xs text-text-secondary">Secured by Clerk</p>
      </div>
    </div>
  );
}
