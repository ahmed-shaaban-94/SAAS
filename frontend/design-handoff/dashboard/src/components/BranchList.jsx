import React from 'react';
import { branches } from '../data/mock.js';

export default function BranchList() {
  return (
    <div className="rounded-card bg-card border border-border/40 p-6">
      <header className="flex items-center gap-3 mb-3">
        <h3 className="text-[15px] font-semibold">Top branches</h3>
        <span className="font-mono text-[11px] text-ink-tertiary">by revenue · MTD</span>
      </header>

      <ul className="flex flex-col">
        {branches.map((b) => (
          <li key={b.name} className="flex items-center gap-3 py-2.5 border-t first:border-t-0 border-border/30">
            <div className={[
              'w-8 h-8 rounded-lg grid place-items-center font-mono text-[12px] font-bold tabular',
              b.rank === 1 ? 'bg-chart-amber/20 text-chart-amber' : 'bg-elevated text-ink-secondary',
            ].join(' ')}>
              {String(b.rank).padStart(2, '0')}
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-[13.5px] truncate">{b.name}</div>
              <div className="text-[11.5px] text-ink-tertiary truncate">
                {b.region} · {b.staff} staff
              </div>
            </div>
            <div className="tabular font-semibold text-[13px]">{b.revenue}</div>
            <div className={[
              'w-14 text-right text-[12.5px] tabular font-semibold',
              b.delta.dir === 'up' ? 'text-growth-green' : 'text-growth-red',
            ].join(' ')}>
              {b.delta.dir === 'up' ? '▲' : '▼'} {b.delta.pct}%
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
