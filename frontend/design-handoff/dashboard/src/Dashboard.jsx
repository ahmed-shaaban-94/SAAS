import React from 'react';
import Sidebar from './components/Sidebar.jsx';
import AlertBanner from './components/AlertBanner.jsx';
import KpiCard from './components/KpiCard.jsx';
import RevenueChart from './components/RevenueChart.jsx';
import ChannelDonut from './components/ChannelDonut.jsx';
import InventoryTable from './components/InventoryTable.jsx';
import ExpiryHeatmap from './components/ExpiryHeatmap.jsx';
import BranchList from './components/BranchList.jsx';
import AnomalyFeed from './components/AnomalyFeed.jsx';
import PipelineHealth from './components/PipelineHealth.jsx';
import { greeting, kpis, alert as alertData } from './data/mock.js';

/**
 * Top-level Dashboard page.
 * Layout: 248px sidebar | main content column.
 * Uses Tailwind utilities + tokens defined in tailwind.config.js + tokens.css.
 */
export default function Dashboard() {
  return (
    <div className="min-h-screen bg-page-glow text-ink-primary font-sans grid grid-cols-[248px_1fr]">
      <Sidebar />

      <main className="px-8 py-7 pb-16 max-w-[1600px]">
        {/* Title row */}
        <header className="flex flex-wrap items-end gap-5 mb-6">
          <div className="flex-1 min-w-[320px]">
            <div className="text-sm text-ink-secondary flex items-center gap-2">
              Good morning, {greeting.name} — here's the pulse for{' '}
              <b className="text-ink-primary">{greeting.dateLabel}</b>
              <LiveBadge label={`Synced ${greeting.syncedAgo}`} />
            </div>
            <h1 className="text-3xl font-bold tracking-tight mt-1">
              Daily operations overview
            </h1>
          </div>
          <PageActions />
        </header>

        <AlertBanner data={alertData} />

        {/* KPI row */}
        <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mt-5">
          {kpis.map((k) => (
            <KpiCard key={k.id} {...k} />
          ))}
        </section>

        {/* Revenue + Channel */}
        <section className="grid grid-cols-1 xl:grid-cols-[2fr_1fr] gap-4 mt-5">
          <RevenueChart />
          <ChannelDonut />
        </section>

        {/* Inventory (2) + Expiry (1) */}
        <section className="grid grid-cols-1 xl:grid-cols-3 gap-4 mt-5">
          <div className="xl:col-span-2">
            <InventoryTable />
          </div>
          <ExpiryHeatmap />
        </section>

        {/* Branches + Anomalies + Pipeline */}
        <section className="grid grid-cols-1 xl:grid-cols-3 gap-4 mt-5">
          <BranchList />
          <AnomalyFeed />
          <PipelineHealth />
        </section>
      </main>
    </div>
  );
}

function LiveBadge({ label }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] text-accent-strong font-mono uppercase tracking-wider">
      <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
      {label}
    </span>
  );
}

function PageActions() {
  const [period, setPeriod] = React.useState('Month');
  const periods = ['Day', 'Week', 'Month', 'Quarter', 'YTD'];
  return (
    <div className="flex items-center gap-3 ml-auto">
      <div className="inline-flex p-1 rounded-full bg-card/80 border border-border/40">
        {periods.map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={[
              'px-3.5 py-1.5 rounded-full text-[13px] transition',
              period === p
                ? 'bg-elevated text-ink-primary shadow-[inset_0_0_0_1px_rgba(0,199,242,0.3)]'
                : 'text-ink-secondary hover:text-ink-primary',
            ].join(' ')}
          >
            {p}
          </button>
        ))}
      </div>
      <button className="px-3.5 py-2 rounded-lg border border-border/60 text-[13px] inline-flex items-center gap-2 hover:bg-elevated/60">
        {/* Replace with your icon system */}
        <span aria-hidden>↓</span> Export
      </button>
      <button className="px-3.5 py-2 rounded-lg bg-accent text-page font-semibold text-[13px] inline-flex items-center gap-2 hover:bg-accent-strong">
        <span aria-hidden>+</span> New report
      </button>
    </div>
  );
}
