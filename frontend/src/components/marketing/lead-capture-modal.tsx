"use client";

import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

type FormState = "idle" | "loading" | "success" | "error";

const USE_CASES = [
  "Sales & Revenue Reporting",
  "Inventory & Expiry Monitoring",
  "Branch Performance Tracking",
  "Operations Reporting",
  "Other",
] as const;

const TEAM_SIZES = ["1–5", "6–20", "21–100", "100+"] as const;

interface Props {
  trigger: string;
  tier?: string;
  triggerClassName?: string;
}

export function LeadCaptureModal({ trigger, tier, triggerClassName }: Props) {
  const [open, setOpen] = useState(false);
  const [formState, setFormState] = useState<FormState>("idle");
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = Object.fromEntries(new FormData(form).entries());

    setFormState("loading");
    try {
      const res = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...data, tier: tier ?? data.tier }),
      });
      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        throw new Error(json.message || "Something went wrong. Please try again.");
      }
      setFormState("success");
    } catch (err) {
      setFormState("error");
      setErrorMessage(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <button
          type="button"
          className={triggerClassName ?? "rounded-full bg-accent px-8 py-3.5 text-sm font-semibold text-page shadow-[0_0_24px_rgba(0,199,242,0.35)] transition-all hover:shadow-[0_0_32px_rgba(0,199,242,0.5)] hover:scale-[1.02]"}
        >
          {trigger}
        </button>
      </Dialog.Trigger>

      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm" />
        <Dialog.Content
          className={cn(
            "fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2",
            "rounded-[1.75rem] border border-border bg-card p-8 shadow-2xl focus:outline-none",
          )}
          aria-describedby="lead-modal-desc"
        >
          <Dialog.Close className="absolute right-4 top-4 rounded-full p-1.5 text-text-secondary hover:bg-background/60 hover:text-text-primary">
            <X className="h-4 w-4" />
            <span className="sr-only">Close</span>
          </Dialog.Close>

          {formState === "success" ? (
            <div className="flex flex-col items-center gap-3 py-6 text-center">
              <CheckCircle2 className="h-10 w-10 text-accent" />
              <Dialog.Title className="text-lg font-semibold">You&apos;re on the list!</Dialog.Title>
              <p className="text-sm text-text-secondary">We&apos;ll be in touch soon to set up your pilot.</p>
              <button
                type="button"
                onClick={() => { setOpen(false); setFormState("idle"); }}
                className="mt-2 rounded-full bg-accent px-6 py-2 text-sm font-semibold text-page"
              >
                Done
              </button>
            </div>
          ) : (
            <>
              <Dialog.Title className="text-lg font-semibold">
                {tier ? `Apply for ${tier}` : "Request Pilot Access"}
              </Dialog.Title>
              <p id="lead-modal-desc" className="mt-1 text-sm text-text-secondary">
                Tell us a bit about your team and we&apos;ll be in touch to get started.
              </p>

              <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                <div>
                  <label htmlFor="lm-email" className="mb-1 block text-xs font-medium text-text-primary">
                    Work Email *
                  </label>
                  <input
                    id="lm-email"
                    name="email"
                    type="email"
                    required
                    placeholder="you@company.com"
                    className="w-full rounded-lg border border-border bg-background/60 px-3 py-2 text-sm placeholder:text-text-secondary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                    aria-label="Email address"
                  />
                </div>

                <div>
                  <label htmlFor="lm-name" className="mb-1 block text-xs font-medium text-text-primary">
                    Your Name
                  </label>
                  <input
                    id="lm-name"
                    name="name"
                    type="text"
                    placeholder="Ahmed Hassan"
                    className="w-full rounded-lg border border-border bg-background/60 px-3 py-2 text-sm placeholder:text-text-secondary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                    aria-label="Name"
                  />
                </div>

                <div>
                  <label htmlFor="lm-company" className="mb-1 block text-xs font-medium text-text-primary">
                    Company
                  </label>
                  <input
                    id="lm-company"
                    name="company"
                    type="text"
                    placeholder="Pharma Group"
                    className="w-full rounded-lg border border-border bg-background/60 px-3 py-2 text-sm placeholder:text-text-secondary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                    aria-label="Company"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="lm-use-case" className="mb-1 block text-xs font-medium text-text-primary">
                      Primary Use Case
                    </label>
                    <select
                      id="lm-use-case"
                      name="use_case"
                      className="w-full rounded-lg border border-border bg-background/60 px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                    >
                      <option value="">Select…</option>
                      {USE_CASES.map((uc) => (
                        <option key={uc} value={uc}>{uc}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="lm-team-size" className="mb-1 block text-xs font-medium text-text-primary">
                      Team Size
                    </label>
                    <select
                      id="lm-team-size"
                      name="team_size"
                      className="w-full rounded-lg border border-border bg-background/60 px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                    >
                      <option value="">Select…</option>
                      {TEAM_SIZES.map((ts) => (
                        <option key={ts} value={ts}>{ts}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {formState === "error" && (
                  <div className="flex items-center gap-1.5 text-growth-red" aria-live="polite">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    <span className="text-xs">{errorMessage}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={formState === "loading"}
                  className="mt-2 w-full rounded-lg bg-accent py-3 text-sm font-semibold text-page transition-colors hover:bg-accent/90 disabled:opacity-60"
                >
                  {formState === "loading" ? (
                    <Loader2 className="mx-auto h-4 w-4 animate-spin" />
                  ) : (
                    "Submit Request"
                  )}
                </button>
              </form>
            </>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
