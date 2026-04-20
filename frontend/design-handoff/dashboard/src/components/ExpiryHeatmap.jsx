import React from 'react';
import { expiryHeat, expiryTiers } from '../data/mock.js';

const palette = [
  'rgba(51,80,107,0.25)',
  'rgba(255,171,61,0.2)',
  'rgba(255,171,61,0.4)',
  'rgba(255,171,61,0.65)',
  'rgba(255,123,123,0.7)',
  '#ff7b7b',
];

const tierCls = {
  red: 'text-growth-red',
  amber: 'text-chart-amber',
  green: 'text-growth-green',
};

export default function ExpiryHeatmap() {
  return (
    <div className="rounded-card bg-card border border-border/40 p-6">
      <header className="flex items-center gap-3 mb-2">
        <h3 className="text-[15px] font-semibold">Expiry calendar</h3>
        <span className="font-mono text-[11px] text-ink-tertiary">next 14 weeks</span>
      </header>
      <p className="text-[12.5px] text-ink-secondary mb-3">
        <b className="text-ink-primary">EGP 142K</b> exposure across{' '}
        <b className="text-ink-primary">12 batches</b>. Quarantine flow is active.
      </p>

      {/* 14 weeks × 7 days */}
      <div className="grid grid-cols-14 gap-1" style={{ gridTemplateColumns: 'repeat(14, minmax(0, 1fr))' }}>
        {expiryHeat.map((w, i) => (
          <div
            key={i}
            className="aspect-square rounded-[3px]"
            style={{ background: palette[Math.min(w, palette.length - 1)] }}
            title={`Week ${Math.floor(i / 7) + 1} day ${(i % 7) + 1} · severity ${w}`}
          />
        ))}
      </div>

      <div className="flex items-center gap-1.5 mt-3 text-[11px] text-ink-tertiary">
        <span>Low</span>
        {palette.slice(1).map((p, i) => (
          <span key={i} className="w-3 h-3 rounded-[2px]" style={{ background: p }} />
        ))}
        <span>High</span>
      </div>

      <div className="mt-4 pt-3 border-t border-border/35 flex flex-col gap-2.5">
        {expiryTiers.map((t) => (
          <div key={t.label} className="flex justify-between text-[12.5px]">
            <span className="text-ink-secondary">{t.label}</span>
            <span className={`tabular font-semibold ${tierCls[t.tone]}`}>{t.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
