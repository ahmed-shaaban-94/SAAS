import React from 'react';
import { channels } from '../data/mock.js';

const colorHex = {
  blue: '#20bce5',
  purple: '#7467f8',
  amber: '#ffab3d',
  green: '#1dd48b',
};

/**
 * Channel split donut + breakdown list.
 * Donut is hand-rolled with stroke-dasharray. Swap with Recharts <PieChart>
 * or Nivo <ResponsivePie> if preferred.
 */
export default function ChannelDonut() {
  const R = 48;
  const C = 2 * Math.PI * R; // 301.59
  let offset = 0;
  const segments = channels.map((ch) => {
    const len = (ch.pct / 100) * C;
    const seg = { ...ch, dash: `${len} ${C}`, offset };
    offset -= len;
    return seg;
  });

  return (
    <div className="rounded-card bg-card border border-border/40 p-6 flex flex-col">
      <header className="flex items-center gap-3 mb-3">
        <h3 className="text-[15px] font-semibold">Channel split</h3>
        <span className="font-mono text-[11px] text-ink-tertiary">month-to-date</span>
      </header>

      <div className="flex items-center gap-5 py-1">
        <svg width="140" height="140" viewBox="0 0 120 120" className="shrink-0">
          <g transform="rotate(-90 60 60)">
            {segments.map((s) => (
              <circle
                key={s.label}
                cx="60" cy="60" r={R}
                fill="none"
                stroke={colorHex[s.color]}
                strokeWidth="18"
                strokeDasharray={s.dash}
                strokeDashoffset={s.offset}
              />
            ))}
          </g>
          <text x="60" y="58" textAnchor="middle" fill="#f7fbff" fontSize="20" fontWeight="700">4.28M</text>
          <text x="60" y="74" textAnchor="middle" fill="#8597a8" fontSize="9" letterSpacing="1.5">TOTAL EGP</text>
        </svg>

        <ul className="flex-1 space-y-2">
          {channels.map((ch) => (
            <li key={ch.label} className="flex items-center gap-2.5 text-[13px]">
              <span className="w-2 h-2 rounded-full" style={{ background: colorHex[ch.color] }} />
              <span className="text-ink-secondary flex-1 truncate">{ch.label}</span>
              <span className="w-20 h-1 rounded-full bg-border/40 overflow-hidden">
                <span className="block h-full" style={{ background: colorHex[ch.color], width: `${ch.pct}%` }} />
              </span>
              <span className="tabular text-ink-primary font-semibold w-10 text-right">{ch.pct}%</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-4 pt-3 border-t border-border/35 text-[12.5px] text-ink-secondary flex items-center gap-2">
        <span aria-hidden className="text-growth-green">↗</span>
        Online channel up <b className="text-growth-green">+34%</b> MoM — fastest-growing segment.
      </div>
    </div>
  );
}
