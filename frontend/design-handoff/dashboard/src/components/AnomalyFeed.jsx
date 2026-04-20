import React from 'react';
import { anomalies } from '../data/mock.js';

const iconByKind = {
  up:   { glyph: '↗', cls: 'bg-growth-green/15 text-growth-green' },
  down: { glyph: '↘', cls: 'bg-growth-red/15 text-growth-red' },
  info: { glyph: 'i', cls: 'bg-chart-purple/15 text-chart-purple' },
};

export default function AnomalyFeed() {
  return (
    <div className="rounded-card bg-card border border-border/40 p-6">
      <header className="flex items-center gap-3 mb-3">
        <h3 className="text-[15px] font-semibold">Anomalies &amp; insights</h3>
        <span className="font-mono text-[11px] text-ink-tertiary">AI · last 24h</span>
      </header>
      <ul className="flex flex-col gap-4">
        {anomalies.map((a, i) => {
          const ico = iconByKind[a.kind];
          return (
            <li key={i} className="flex gap-3">
              <div className={`w-7 h-7 rounded-lg grid place-items-center shrink-0 text-[13px] font-semibold ${ico.cls}`}>
                {ico.glyph}
              </div>
              <div className="flex-1 min-w-0">
                <h5 className="font-semibold text-[13.5px]">{a.title}</h5>
                <p className="text-[12.5px] text-ink-secondary mt-0.5 leading-snug">{a.body}</p>
                <div className="font-mono text-[10.5px] uppercase tracking-[0.18em] text-ink-tertiary mt-1.5">
                  {a.time} · {a.confidence} confidence
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
