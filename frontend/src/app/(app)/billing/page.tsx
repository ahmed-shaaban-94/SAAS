"use client";

import { useState } from "react";
import { CreditCard, ExternalLink, CheckCircle2, AlertCircle, Zap } from "lucide-react";
import { useBilling, createCheckout, createPortalSession } from "@/hooks/use-billing";
import { useToast } from "@/components/ui/toast";

function UsageMeter({
  label,
  used,
  limit,
}: {
  label: string;
  used: number;
  limit: number;
}) {
  const isUnlimited = limit === -1;
  const pct = isUnlimited ? 0 : Math.min((used / limit) * 100, 100);
  const isNearLimit = !isUnlimited && pct >= 80;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-text-secondary">{label}</span>
        <span className="font-medium text-text-primary">
          {used.toLocaleString()} / {isUnlimited ? "Unlimited" : limit.toLocaleString()}
        </span>
      </div>
      <div className="h-2 rounded-full bg-border">
        <div
          className={`h-full rounded-full transition-all ${
            isNearLimit ? "bg-growth-red" : "bg-accent"
          }`}
          style={{ width: isUnlimited ? "0%" : `${pct}%` }}
        />
      </div>
    </div>
  );
}

function FeatureFlag({ label, enabled }: { label: string; enabled: boolean }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      {enabled ? (
        <CheckCircle2 className="h-4 w-4 text-accent" />
      ) : (
        <AlertCircle className="h-4 w-4 text-text-secondary" />
      )}
      <span className={enabled ? "text-text-primary" : "text-text-secondary"}>
        {label}
      </span>
    </div>
  );
}

export default function BillingPage() {
  const { billing, isLoading, isError } = useBilling();
  const { error: toastError, info } = useToast();
  const [isRedirecting, setIsRedirecting] = useState(false);

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl space-y-6 p-6">
        <h1 className="text-2xl font-bold text-text-primary">Billing</h1>
        <div className="animate-pulse space-y-4">
          <div className="h-48 rounded-xl bg-card" />
          <div className="h-32 rounded-xl bg-card" />
        </div>
      </div>
    );
  }

  if (isError || !billing) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <h1 className="text-2xl font-bold text-text-primary">Billing</h1>
        <p className="mt-4 text-text-secondary">
          Unable to load billing information. Please try again later.
        </p>
      </div>
    );
  }

  const isStarter = billing.plan === "starter";
  const isPastDue = billing.subscription_status === "past_due";

  async function handleUpgrade() {
    setIsRedirecting(true);
    info("Redirecting to checkout...");
    try {
      const url = await createCheckout(
        process.env.NEXT_PUBLIC_STRIPE_PRICE_PRO_MONTHLY || "",
      );
      window.location.href = url;
    } catch {
      toastError("Failed to start checkout. Please try again.");
      setIsRedirecting(false);
    }
  }

  async function handleManage() {
    setIsRedirecting(true);
    info("Opening billing portal...");
    try {
      const url = await createPortalSession();
      window.location.href = url;
    } catch {
      toastError("Failed to open billing portal. Please try again.");
      setIsRedirecting(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <h1 className="text-2xl font-bold text-text-primary">Billing</h1>

      {/* Plan Card */}
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <CreditCard className="h-5 w-5 text-accent" />
              <h2 className="text-lg font-semibold text-text-primary">
                {billing.plan_name} Plan
              </h2>
            </div>
            <p className="mt-1 text-2xl font-bold text-text-primary">
              {billing.price_display}
            </p>
            {billing.current_period_end && (
              <p className="mt-1 text-sm text-text-secondary">
                {billing.cancel_at_period_end ? "Cancels" : "Renews"} on{" "}
                {new Date(billing.current_period_end).toLocaleDateString()}
              </p>
            )}
            {isPastDue && (
              <p className="mt-2 text-sm font-medium text-growth-red">
                Payment failed — please update your payment method.
              </p>
            )}
          </div>

          <div>
            {isStarter ? (
              <button
                onClick={handleUpgrade}
                disabled={isRedirecting}
                className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-page transition-colors hover:bg-accent/90 disabled:opacity-60"
              >
                <Zap className="h-4 w-4" />
                {isRedirecting ? "Redirecting..." : "Upgrade to Pro"}
              </button>
            ) : (
              <button
                onClick={handleManage}
                disabled={isRedirecting}
                className="flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium text-text-primary transition-colors hover:bg-card disabled:opacity-60"
              >
                <ExternalLink className="h-4 w-4" />
                {isRedirecting ? "Redirecting..." : "Manage Subscription"}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Usage */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-text-secondary">
          Usage
        </h3>
        <div className="space-y-4">
          <UsageMeter
            label="Data Sources"
            used={billing.data_sources_used}
            limit={billing.data_sources_limit}
          />
          <UsageMeter
            label="Total Rows"
            used={billing.total_rows_used}
            limit={billing.total_rows_limit}
          />
        </div>
      </div>

      {/* Features */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-text-secondary">
          Features
        </h3>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <FeatureFlag label="AI Insights" enabled={billing.ai_insights} />
          <FeatureFlag label="Pipeline Automation" enabled={billing.pipeline_automation} />
          <FeatureFlag label="Quality Gates" enabled={billing.quality_gates} />
          <FeatureFlag label="Basic Dashboard" enabled />
        </div>
      </div>
    </div>
  );
}
