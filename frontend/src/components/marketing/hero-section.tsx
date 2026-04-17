"use client";

import Link from "next/link";

const KPI_ITEMS = [
  { label: "Faster weekly reporting",           value: "Automated" },
  { label: "Earlier stock & expiry visibility", value: "30+ days"  },
  { label: "View across sales & operations",    value: "One system"},
];

const DASHBOARD_KPIS = [
  { label: "Total Revenue", value: "EGP 4.2M", change: "+12.5%" },
  { label: "Orders", value: "23,847", change: "+8.3%" },
  { label: "Customers", value: "1,245", change: "+15.2%" },
  { label: "Avg. Order", value: "EGP 176", change: "+4.1%" },
];

const BAR_HEIGHTS = [32, 48, 44, 68, 61, 82, 74, 92, 86, 108, 96, 124];
const FORECAST_HEIGHTS = [42, 56, 74, 68, 92];

export function HeroSection() {
  return (
    <section className="relative overflow-hidden px-4 pb-16 pt-28 sm:px-6 md:pb-24 md:pt-36 lg:px-8">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute left-[-8%] top-[-8%] h-[420px] w-[420px] rounded-full bg-accent/20 blur-[120px]" />
        <div className="absolute right-[-6%] top-[12%] h-[340px] w-[340px] rounded-full bg-chart-purple/20 blur-[120px]" />
        <div className="absolute inset-x-0 top-24 h-[520px] bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.14),transparent_60%)]" />
      </div>

      <div className="relative mx-auto grid max-w-7xl gap-12 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
        <div className="max-w-3xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-accent shadow-[0_10px_30px_rgba(0,199,242,0.12)]">
            <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />
            Built for pharma sales and operations teams
          </div>

          <h1 className="max-w-4xl text-4xl font-bold leading-[1.02] tracking-tight sm:text-5xl md:text-6xl lg:text-7xl">
            Turn pharma sales and operations data into{" "}
            <span className="gradient-text-animated">daily decisions</span>
          </h1>

          <p className="mt-6 max-w-2xl text-lg text-text-secondary sm:text-xl">
            Upload spreadsheets or connect your data sources, clean them automatically,
            monitor revenue, branch performance, inventory health, and expiry risk, and
            give your team one dashboard they can act on every day.
          </p>

          <div className="mt-8 grid max-w-2xl gap-3 sm:grid-cols-3">
            {KPI_ITEMS.map((item) => (
              <div key={item.label} className="viz-panel-soft rounded-2xl px-4 py-3">
                <p className="text-[11px] uppercase tracking-[0.22em] text-text-secondary">{item.label}</p>
                <p className="mt-2 text-2xl font-bold text-text-primary">{item.value}</p>
              </div>
            ))}
          </div>

          <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-start">
            <Link
              href="#pilot-access"
              className="rounded-full bg-accent px-8 py-3.5 text-sm font-semibold text-page shadow-[0_0_24px_rgba(0,199,242,0.35)] transition-all hover:shadow-[0_0_32px_rgba(0,199,242,0.5)] hover:scale-[1.02]"
            >
              Request Pilot Access
            </Link>
            <Link
              href="/demo"
              className="rounded-full border border-white/15 bg-white/5 px-8 py-3.5 text-sm font-semibold text-text-primary transition-colors hover:bg-white/10"
            >
              See Product Demo
            </Link>
          </div>

          <p className="mt-4 text-sm text-text-secondary/70">
            Best for commercial leaders, operations teams, and pharmacy groups that need
            clearer decisions without rebuilding their data stack from scratch.
          </p>
        </div>

        <div className="relative mx-auto w-full max-w-5xl float-card">
          <div className="absolute -left-6 top-14 hidden rounded-[1.6rem] border border-white/10 bg-white/5 p-4 backdrop-blur md:block">
            <p className="text-[11px] uppercase tracking-[0.22em] text-text-secondary">Customer mix</p>
            <div className="mt-4 h-28 w-28 rounded-full border-[16px] border-chart-blue/80 border-r-chart-amber border-t-growth-green bg-transparent" />
          </div>

          <div className="absolute -right-4 bottom-10 hidden rounded-[1.6rem] border border-white/10 bg-white/5 p-4 backdrop-blur md:block">
            <p className="text-[11px] uppercase tracking-[0.22em] text-text-secondary">Forecast</p>
            <div className="mt-4 flex items-end gap-2">
              {FORECAST_HEIGHTS.map((height) => (
                <div
                  key={height}
                  className="w-6 rounded-full bg-gradient-to-t from-chart-purple to-accent"
                  style={{ height: `${height}px` }}
                />
              ))}
            </div>
          </div>

          <div className="viz-panel relative overflow-hidden rounded-[2rem] p-5 shadow-[0_30px_120px_rgba(0,0,0,0.25)]">
            <div className="absolute inset-x-8 top-0 h-1 rounded-b-full bg-gradient-to-r from-accent via-chart-purple to-chart-amber" />

            <div className="mb-5 flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-growth-red/70" />
              <div className="h-3 w-3 rounded-full bg-chart-amber/70" />
              <div className="h-3 w-3 rounded-full bg-growth-green/70" />
              <span className="ml-2 text-xs uppercase tracking-[0.2em] text-text-secondary">
                Data Pulse Dashboard
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {DASHBOARD_KPIS.map((kpi) => (
                <div key={kpi.label} className="viz-panel-soft rounded-2xl p-3">
                  <p className="text-[11px] uppercase tracking-[0.18em] text-text-secondary">{kpi.label}</p>
                  <p className="mt-2 text-lg font-bold">{kpi.value}</p>
                  <p className="mt-1 text-xs text-growth-green">{kpi.change}</p>
                </div>
              ))}
            </div>

            <div className="mt-5 grid gap-4 lg:grid-cols-[1.35fr_0.65fr]">
              <div className="viz-panel-soft rounded-[1.7rem] p-4">
                <p className="text-[11px] uppercase tracking-[0.22em] text-text-secondary">Revenue Trend</p>
                <div className="viz-grid-surface mt-4 rounded-[1.2rem] px-2 pb-3 pt-6">
                  <div className="relative h-40">
                    <div className="absolute inset-x-0 bottom-0 h-[2px] rounded-full bg-white/10" />
                    <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(0,199,242,0.18),transparent_60%)]" />
                    <div className="absolute inset-0 flex items-end gap-2">
                      {BAR_HEIGHTS.map((height, index) => (
                        <div key={`${height}-${index}`} className="relative flex-1">
                          <div
                            className="absolute inset-x-0 bottom-0 rounded-full bg-gradient-to-t from-chart-blue/10 to-transparent"
                            style={{ height: `${height + 24}px` }}
                          />
                          <div className="rounded-full bg-gradient-to-t from-chart-blue to-chart-purple" style={{ height: `${height}px` }} />
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="viz-panel-soft rounded-[1.7rem] p-4">
                  <p className="text-[11px] uppercase tracking-[0.22em] text-text-secondary">Channel Split</p>
                  <div className="mt-4 h-32 rounded-full border-[18px] border-chart-blue/80 border-r-chart-amber border-t-growth-green border-l-chart-purple" />
                </div>

                <div className="viz-panel-soft rounded-[1.7rem] p-4">
                  <p className="text-[11px] uppercase tracking-[0.22em] text-text-secondary">Momentum</p>
                  <div className="mt-4 flex items-center justify-between">
                    <span className="text-3xl font-bold text-growth-green">+23%</span>
                    <span className="rounded-full bg-growth-green/10 px-3 py-1 text-xs font-semibold text-growth-green">Healthy</span>
                  </div>
                  <div className="mt-4 h-2 rounded-full bg-white/10">
                    <div className="h-2 w-[72%] rounded-full bg-gradient-to-r from-accent to-growth-green" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
