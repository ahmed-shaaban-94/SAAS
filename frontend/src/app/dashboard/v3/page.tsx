/**
 * /dashboard/v3 — new dashboard design (epic #501).
 *
 * Port of the design handoff at frontend/design-handoff/dashboard/.
 * This is parallel to /dashboard until parity + sign-off; see issue #502.
 *
 * Wired widgets (against mock-fixtures for now):
 *   - Sidebar, KPI row (4 cards), AI alert banner, page actions, greeting
 *
 * Pending real API wiring (per issues #503–#510):
 *   - RevenueChart, ChannelDonut, InventoryTable, ExpiryHeatmap,
 *     BranchList, AnomalyFeed, PipelineHealth
 */

import { Sidebar } from "@/components/dashboard/v3/sidebar";
import { AlertBanner } from "@/components/dashboard/v3/alert-banner";
import { KpiCard } from "@/components/dashboard/v3/kpi-card";
import { PageActions } from "@/components/dashboard/v3/page-actions";
import { PlaceholderCard } from "@/components/dashboard/v3/placeholder-card";
import { alert, greeting, kpis } from "@/components/dashboard/v3/mock-fixtures";

export const metadata = {
  title: "Daily operations overview",
};

export default function DashboardV3Page() {
  return (
    <div className="grid min-h-screen grid-cols-[248px_1fr] font-sans">
      <Sidebar />

      <main id="main-content" className="max-w-[1600px] px-8 py-7 pb-16">
        <header className="mb-6 flex flex-wrap items-end gap-5">
          <div className="min-w-[320px] flex-1">
            <div className="flex items-center gap-2 text-sm text-text-secondary">
              Good morning, {greeting.name} — here&apos;s the pulse for{" "}
              <b className="text-text-primary">{greeting.dateLabel}</b>
              <LiveBadge label={`Synced ${greeting.syncedAgo}`} />
            </div>
            <h1 className="mt-1 text-3xl font-bold tracking-tight">
              Daily operations overview
            </h1>
          </div>
          <PageActions />
        </header>

        <AlertBanner data={alert} />

        <section
          aria-label="Key metrics"
          className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4"
        >
          {kpis.map((k) => (
            <KpiCard key={k.id} {...k} />
          ))}
        </section>

        <section className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-[2fr_1fr]">
          <PlaceholderCard
            title="Revenue + Forecast"
            note="Composite chart (actual + forecast + target + today marker) — wiring blocked on /analytics/revenue-forecast."
            issueNumber={504}
            minHeight={320}
          />
          <PlaceholderCard
            title="Channel mix"
            note="Donut split across retail / wholesale / institution / online — wiring blocked on /analytics/channels."
            issueNumber={505}
            minHeight={320}
          />
        </section>

        <section className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-3">
          <PlaceholderCard
            title="Reorder watchlist"
            note="Low-stock SKUs with velocity and days-of-stock — wiring blocked on enriched /inventory/reorder-alerts."
            issueNumber={507}
            className="xl:col-span-2"
          />
          <PlaceholderCard
            title="Expiry exposure"
            note="14×7 heatmap + 30/60/90 tier summary (EGP) — wiring blocked on /expiry/exposure-summary."
            issueNumber={506}
          />
        </section>

        <section className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-3">
          <PlaceholderCard
            title="Top branches"
            note="Ranked branch list with staff count — wiring blocked on extended /analytics/sites."
            issueNumber={507}
          />
          <PlaceholderCard
            title="Anomalies feed"
            note="Up/down/info anomaly cards with confidence — wiring blocked on /anomalies/cards."
            issueNumber={508}
          />
          <PlaceholderCard
            title="Pipeline health"
            note="Bronze/Silver/Gold nodes + gates + tests + 7-day history — wiring blocked on /pipeline/health."
            issueNumber={509}
          />
        </section>
      </main>
    </div>
  );
}

function LiveBadge({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-wider text-accent-strong">
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
      {label}
    </span>
  );
}
