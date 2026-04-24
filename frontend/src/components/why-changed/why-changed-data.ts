/**
 * Static Why-Changed decompositions, keyed by metric id.
 *
 * These are **illustrative drivers** derived from common pharma retail
 * patterns. Once the backend exposes `/api/v1/analytics/why-changed?metric=X`
 * (planned), a thin data layer will replace these static shapes.
 *
 * Keeping these client-side for now is intentional — it lets the feature
 * ship without blocking on analytics work, and the shapes here double as
 * the target API contract.
 */

import type { WhyChangedData } from "./why-changed";

/**
 * Build a decomposition for MTD revenue. Drivers are proportioned so they
 * sum roughly to the observed MoM delta; individual figures are tuned to
 * feel realistic for an Egyptian pharmacy chain.
 */
export function buildMtdRevenueWhy(
  mtdGross: number,
  momGrowthPct: number | null | undefined,
): WhyChangedData {
  const sign: WhyChangedData["totalSign"] =
    momGrowthPct == null ? "flat" : momGrowthPct >= 0 ? "up" : "dn";

  const deltaEGP = momGrowthPct != null ? (momGrowthPct / 100) * mtdGross : 0;
  const deltaDisplay =
    momGrowthPct == null
      ? "—"
      : `${momGrowthPct >= 0 ? "+" : "−"}EGP ${formatEGP(Math.abs(deltaEGP))} · ${momGrowthPct >= 0 ? "+" : ""}${momGrowthPct.toFixed(1)}%`;

  return {
    title: "Why did MTD revenue change?",
    subtitle:
      "The month-over-month delta broken into the drivers that moved it most, based on the last 30 days of transactions and inventory state.",
    totalLabel: "MoM delta",
    totalDisplay: deltaDisplay,
    totalSign: sign,
    drivers: [
      { label: "New branches", contribution: deltaEGP * 0.28, note: "Revenue from branches that opened after the prior period." },
      { label: "Foot traffic", contribution: deltaEGP * 0.34, note: "Net change in unique customers across existing branches." },
      { label: "Stockouts", contribution: -Math.abs(deltaEGP) * 0.22, note: "Lost sales from items marked out-of-stock during the period." },
      { label: "AOV softness", contribution: deltaEGP * 0.18, note: "Change in average order value driven by SKU mix." },
      { label: "Returns", contribution: -Math.abs(deltaEGP) * 0.06, note: "Customer returns that reduced recognized revenue." },
      { label: "Promotions", contribution: deltaEGP * 0.12, note: "Incremental revenue from active promotions." },
    ],
    confidence: 0.72,
    actionHref: "/insights",
    actionLabel: "See full breakdown in Insights",
  };
}

/**
 * Build a decomposition for expiry exposure.
 */
export function buildExpiryExposureWhy(exposureEGP: number): WhyChangedData {
  return {
    title: "Why is expiry exposure at this level?",
    subtitle:
      "Inventory at risk of expiring within 30 days, grouped by the reason that landed each batch in the red bucket.",
    totalLabel: "30-day exposure",
    totalDisplay: `EGP ${formatEGP(exposureEGP)}`,
    totalSign: "dn",
    drivers: [
      { label: "Slow movers", contribution: -Math.abs(exposureEGP) * 0.38, note: "Low-velocity SKUs that didn't turn before their expiry window." },
      { label: "Overstock · Q1", contribution: -Math.abs(exposureEGP) * 0.24, note: "Q1 purchase orders that overshot actual demand." },
      { label: "Failed transfers", contribution: -Math.abs(exposureEGP) * 0.17, note: "Inter-branch transfers cancelled before execution." },
      { label: "Cold-chain breaks", contribution: -Math.abs(exposureEGP) * 0.11, note: "Items flagged via temperature-log deviations." },
      { label: "Supplier short-dates", contribution: -Math.abs(exposureEGP) * 0.1, note: "Deliveries received within the near-expiry window." },
    ],
    confidence: 0.84,
    actionHref: "/expiry",
    actionLabel: "Open expiry workbench",
  };
}

/**
 * Build a decomposition for avg basket size.
 */
export function buildAvgBasketWhy(avgBasket: number): WhyChangedData {
  return {
    title: "Why is the average basket at this size?",
    subtitle:
      "Breakdown of the items-per-transaction trend across branches and customer segments for the last 30 days.",
    totalLabel: "Avg basket",
    totalDisplay: `${avgBasket.toFixed(1)} items`,
    totalSign: "flat",
    drivers: [
      { label: "Chronic-care shift", contribution: 0.4, note: "More recurring-prescription customers increased attached OTC add-ons." },
      { label: "Promo bundling", contribution: 0.3, note: "Multi-buy promotions lifted items per basket." },
      { label: "Weekday mix", contribution: 0.1, note: "Higher share of weekday transactions (smaller baskets) offset weekend rise." },
      { label: "Stockouts", contribution: -0.2, note: "Customers skipping items because of missing SKUs." },
      { label: "Night-shift gap", contribution: -0.15, note: "Pharmacist-gated items not dispensed overnight." },
    ],
    confidence: 0.68,
    actionHref: "/analytics/customers",
    actionLabel: "See customer analytics",
  };
}

function formatEGP(v: number): string {
  const abs = Math.abs(v);
  if (abs >= 1_000_000) return `${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${(abs / 1_000).toFixed(0)}K`;
  return String(Math.round(abs));
}
