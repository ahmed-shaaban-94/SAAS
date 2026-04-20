import React from 'react';
import { revenue } from '../data/mock.js';

/**
 * Revenue trend + forecast + target.
 *
 * Prototype uses hand-plotted SVG paths from mock.revenue. When wiring,
 * replace with your charting library of choice, e.g.:
 *   - Recharts: <AreaChart> with two <Area>s (actual solid, forecast dashed)
 *   - Visx: XYChart + AnimatedAreaSeries
 *   - Nivo: ResponsiveLine with custom dashed layer
 * Keep the target dashed reference line, TODAY marker, and forecast band.
 */
export default function RevenueChart() {
  const [mode, setMode] = React.useState('Revenue');
  const modes = ['Revenue', 'Orders', 'AOV'];
  return (
    <div className="rounded-card bg-card border border-border/40 p-6">
      <header className="flex flex-wrap items-center gap-3 mb-4">
        <h3 className="text-[15px] font-semibold">Revenue trend</h3>
        <span className="font-mono text-[11px] text-ink-tertiary">last 30 days · EGP</span>
        <div className="ml-auto flex gap-1">
          {modes.map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={[
                'px-2.5 py-1 rounded-full text-[12px] border transition',
                mode === m
                  ? 'bg-accent/15 text-accent-strong border-accent/40'
                  : 'bg-transparent text-ink-secondary border-border/40 hover:text-ink-primary',
              ].join(' ')}
            >
              {m}
            </button>
          ))}
        </div>
      </header>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <Stat label="This month" value={revenue.thisMonth} delta={`▲ ${revenue.thisMonthDelta}`} tone="green" />
        <Stat label="Forecast (MTD + 12d)" value={revenue.forecast} delta={`${revenue.forecastConfidence}% confidence`} tone="purple" />
        <Stat label="Target" value={revenue.target} delta={revenue.targetStatus} tone="dim" />
      </div>

      <div className="flex items-center gap-4 text-xs text-ink-secondary mb-2">
        <Legend color="#00c7f2" label="Actual" />
        <Legend color="#7467f8" label="Forecast" dim />
        <Legend color="#8597a8" label="Target" dim />
      </div>

      <svg viewBox="0 0 700 240" preserveAspectRatio="none" className="w-full h-[240px]">
        <g stroke="rgba(51,80,107,0.35)" strokeWidth="1">
          {[40, 90, 140, 190].map((y) => <line key={y} x1="0" y1={y} x2="700" y2={y} />)}
        </g>
        <line x1="0" y1="110" x2="700" y2="110" stroke="#8597a8" strokeWidth="1.5" strokeDasharray="4 6" opacity="0.5" />
        <text x="700" y="106" textAnchor="end" fill="#8597a8" fontSize="10" fontFamily="JetBrains Mono">Target {revenue.target.replace('EGP ', '')}</text>

        <defs>
          <linearGradient id="revG" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#00c7f2" stopOpacity="0.35" />
            <stop offset="1" stopColor="#00c7f2" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={`${revenue.actualPath} L500 220 L0 220 Z`} fill="url(#revG)" />
        <path d={revenue.actualPath} stroke="#00c7f2" strokeWidth="2.5" fill="none" strokeLinecap="round" />

        <path d={revenue.forecastPath} stroke="#7467f8" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeDasharray="5 5" />
        <path d={`${revenue.forecastPath} L700 80 C660 86 640 88 600 94 C560 100 540 106 500 115 Z`} fill="#7467f8" opacity="0.08" />

        <circle cx="500" cy="95" r="4" fill="#00c7f2" stroke="#081826" strokeWidth="2" />
        <circle cx="700" cy="60" r="4" fill="#7467f8" stroke="#081826" strokeWidth="2" />
        <line x1={revenue.todayX} y1="95" x2={revenue.todayX} y2="230" stroke="#00c7f2" strokeWidth="1" opacity="0.2" strokeDasharray="2 3" />
        <text x={revenue.todayX} y="230" textAnchor="middle" fill="#00c7f2" fontSize="9.5" fontFamily="JetBrains Mono">TODAY</text>

        <g fill="#8597a8" fontSize="10">
          {revenue.xLabels.map((label, i) => {
            const x = (700 / (revenue.xLabels.length - 1)) * i;
            const anchor = i === 0 ? 'start' : i === revenue.xLabels.length - 1 ? 'end' : 'middle';
            return <text key={label} x={x} y="230" textAnchor={anchor}>{label}</text>;
          })}
        </g>
      </svg>
    </div>
  );
}

function Stat({ label, value, delta, tone }) {
  const toneCls =
    tone === 'green' ? 'text-growth-green' :
    tone === 'purple' ? 'text-chart-purple' :
    'text-ink-tertiary';
  const valueCls = tone === 'purple' ? 'text-chart-purple' : tone === 'dim' ? 'text-ink-secondary' : '';
  return (
    <div>
      <div className="text-xs text-ink-tertiary uppercase tracking-wider">{label}</div>
      <div className={`text-2xl font-bold tabular mt-1 ${valueCls}`}>{value}</div>
      <div className={`text-xs mt-0.5 ${toneCls}`}>{delta}</div>
    </div>
  );
}

function Legend({ color, label, dim }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="w-3 h-1.5 rounded-sm" style={{ background: color, opacity: dim ? 0.5 : 1 }} />
      {label}
    </span>
  );
}
