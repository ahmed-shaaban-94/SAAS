"use client";

import { useState } from "react";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";

type FormState = "idle" | "loading" | "success" | "error";

export function WaitlistForm() {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<FormState>("idle");
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setState("error");
      setErrorMessage("Please enter a valid email address.");
      return;
    }

    setState("loading");
    try {
      const res = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.message || "Something went wrong. Please try again.");
      }

      setState("success");
      setEmail("");
    } catch (err) {
      setState("error");
      setErrorMessage(
        err instanceof Error ? err.message : "Something went wrong. Please try again."
      );
    }
  }

  if (state === "success") {
    return (
      <div className="flex items-center gap-2 text-accent" aria-live="polite">
        <CheckCircle2 className="h-5 w-5" />
        <span className="text-sm font-medium">
          You&apos;re on the list! We&apos;ll be in touch soon.
        </span>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-md">
      <div className="flex gap-3">
        <label htmlFor="waitlist-email" className="sr-only">
          Email address
        </label>
        <input
          id="waitlist-email"
          type="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (state === "error") setState("idle");
          }}
          placeholder="Enter your email"
          className="flex-1 rounded-lg border border-border bg-card px-4 py-3 text-sm text-text-primary placeholder:text-text-secondary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
          disabled={state === "loading"}
          required
        />
        <button
          type="submit"
          disabled={state === "loading"}
          className="rounded-lg bg-accent px-6 py-3 text-sm font-semibold text-page transition-colors hover:bg-accent/90 disabled:opacity-60"
        >
          {state === "loading" ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            "Join Waitlist"
          )}
        </button>
      </div>
      {state === "error" && (
        <div className="mt-2 flex items-center gap-1.5 text-growth-red" aria-live="polite">
          <AlertCircle className="h-4 w-4" />
          <span className="text-xs">{errorMessage}</span>
        </div>
      )}
    </form>
  );
}
