"use client";

import { useState } from "react";
import { AlertCircle, CheckCircle2, CreditCard, ExternalLink, Zap } from "lucide-react";
import { createCheckout, createPortalSession, useBilling } from "@/hooks/use-billing";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { Header } from "@/components/layout/header";
import { LoadingCard } from "@/components/loading-card";
import { PageTransition } from "@/components/layout/page-transition";
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
    <div className="viz-panel-soft rounded-[1.35rem] p-4">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-text-secondary">
          {label}
        </span>
        <span className="font-semibold text-text-primary">
          {used.toLocaleString()} / {isUnlimited ? "Unlimited" : limit.toLocaleString()}
        </span>
      </div>
      <div className="mt-3 h-2.5 rounded-full bg-border/70">
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
    <div className="viz-panel-soft flex items-center gap-3 rounded-[1.2rem] px-4 py-3 text-sm">
      <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-background/60">
        {enabled ? (
          <CheckCircle2 className="h-4 w-4 text-accent" />
        ) : (
          <AlertCircle className="h-4 w-4 text-text-secondary" />
        )}
      </div>
      <span className={enabled ? "font-medium text-text-primary" : "text-text-secondary"}>
        {label}
      </span>
    </div>
  );
}

export default function BillingPage() {
  const { billing, isLoading, isError } = useBilling();
  const { error: toastError, info } = useToast();
  const [isRedirecting, setIsRedirecting] = useState(false);

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

  if (isLoading) {
    return (
      <PageTransition>
        <Breadcrumbs />
        <Header
          title="Billing"
          description="Track plan usage, billing status, and subscription controls"
        />
        <div className="mx-auto max-w-4xl space-y-6">
          <LoadingCard className="h-64 rounded-[1.75rem]" lines={5} />
          <LoadingCard className="h-48 rounded-[1.75rem]" lines={4} />
        </div>
      </PageTransition>
    );
  }

  if (isError || !billing) {
    return (
      <PageTransition>
        <Breadcrumbs />
        <Header
          title="Billing"
          description="Track plan usage, billing status, and subscription controls"
        />
        <div className="mx-auto max-w-4xl">
          <div className="viz-panel rounded-[1.75rem] p-8">
            <p className="text-sm text-text-secondary">
              Unable to load billing information. Please try again later.
            </p>
          </div>
        </div>
      </PageTransition>
    );
  }

  const isStarter = billing.plan === "starter";
  const isPastDue = billing.subscription_status === "past_due";

  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Billing"
        description="Track plan usage, billing status, and subscription controls"
      />

      <div className="mx-auto max-w-4xl space-y-6">
        <section className="viz-panel relative overflow-hidden rounded-[1.9rem] p-6 sm:p-7">
          <div className="absolute inset-x-8 top-0 h-1 rounded-b-full bg-gradient-to-r from-chart-blue via-accent to-chart-amber opacity-90" />
          <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="viz-panel-soft flex h-11 w-11 items-center justify-center rounded-2xl">
                  <CreditCard className="h-5 w-5 text-accent" />
                </div>
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
                    Active Plan
                  </p>
                  <h2 className="mt-2 text-2xl font-bold tracking-tight text-text-primary sm:text-[2rem]">
                    {billing.plan_name} Plan
                  </h2>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <div className="viz-panel-soft rounded-[1.35rem] p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-text-secondary">
                    Price
                  </p>
                  <p className="mt-3 text-xl font-bold text-text-primary">
                    {billing.price_display}
                  </p>
                </div>
                <div className="viz-panel-soft rounded-[1.35rem] p-4 sm:col-span-2">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-text-secondary">
                    Renewal Status
                  </p>
                  <p className="mt-3 text-sm text-text-primary">
                    {billing.current_period_end
                      ? `${billing.cancel_at_period_end ? "Cancels" : "Renews"} on ${new Date(billing.current_period_end).toLocaleDateString()}`
                      : "No renewal date available"}
                  </p>
                  {isPastDue && (
                    <p className="mt-2 text-sm font-medium text-growth-red">
                      Payment failed. Please update your payment method.
                    </p>
                  )}
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-3 lg:min-w-[220px]">
              {isStarter ? (
                <button
                  onClick={handleUpgrade}
                  disabled={isRedirecting}
                  className="inline-flex items-center justify-center gap-2 rounded-2xl bg-accent px-5 py-3 text-sm font-semibold text-page transition-all hover:-translate-y-0.5 hover:bg-accent/90 disabled:opacity-60"
                >
                  <Zap className="h-4 w-4" />
                  {isRedirecting ? "Redirecting..." : "Upgrade to Pro"}
                </button>
              ) : (
                <button
                  onClick={handleManage}
                  disabled={isRedirecting}
                  className="viz-panel-soft inline-flex items-center justify-center gap-2 rounded-2xl px-5 py-3 text-sm font-semibold text-text-primary transition-colors hover:text-accent disabled:opacity-60"
                >
                  <ExternalLink className="h-4 w-4" />
                  {isRedirecting ? "Redirecting..." : "Manage Subscription"}
                </button>
              )}
            </div>
          </div>
        </section>

        <section className="viz-panel rounded-[1.75rem] p-6">
          <h3 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
            Usage Envelope
          </h3>
          <div className="grid gap-4 lg:grid-cols-2">
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
        </section>

        <section className="viz-panel rounded-[1.75rem] p-6">
          <h3 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
            Included Capabilities
          </h3>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <FeatureFlag label="AI Insights" enabled={billing.ai_insights} />
            <FeatureFlag label="Pipeline Automation" enabled={billing.pipeline_automation} />
            <FeatureFlag label="Quality Gates" enabled={billing.quality_gates} />
            <FeatureFlag label="Basic Dashboard" enabled />
          </div>
        </section>
      </div>
    </PageTransition>
  );
}
