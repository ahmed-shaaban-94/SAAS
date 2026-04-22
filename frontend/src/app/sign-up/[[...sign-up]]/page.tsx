import { SignUp } from "@clerk/nextjs";
import { Activity } from "lucide-react";

export default function SignUpPage() {
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
        <SignUp
          routing="path"
          path="/sign-up"
          signInUrl="/sign-in"
          fallbackRedirectUrl="/dashboard"
        />
        <p className="text-center text-xs text-text-secondary">Secured by Clerk</p>
      </div>
    </div>
  );
}
