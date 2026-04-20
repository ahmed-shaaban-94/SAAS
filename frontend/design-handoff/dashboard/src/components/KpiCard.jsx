import React from 'react';

const colorMap = {
  accent: { stroke: '#00c7f2', fill: 'rgba(0,199,242,0.3)', tint: 'bg-accent/15 text-accent' },
  purple: { stroke: '#7467f8', fill: 'rgba(116,103,248,0.3)', tint: 'bg-chart-purple/15 text-chart-purple' },
  amber:  { stroke: '#ffab3d', fill: 'rgba(255,171,61,0.3)', tint: 'bg-chart-amber/15 text-chart-amber' },
  red:    { stroke: '#ff7b7b', fill: 'rgba(255,123,123,0.3)', tint: 'bg-growth-red/15 text-growth-red' },
};

/**
 * A KPI tile. Props match data/mock.js KPI shape.
 * Replace <svg> sparkline with a real chart lib (Recharts <Sparkline/>) when wiring.
 */
export default function KpiCard({
  label, value, valueSuffix, delta, sub, color = 'accent', sparkline = [],
}) {
  const c = colorMap[color] ?? colorMap.accent;
  const id = React.useId();
  return (
    <div className="relative overflow-hidden rounded-card bg-card border border-border/40 p-5 flex flex-col gap-2">
      <div className="flex items-center gap-2.5">
        <div className={`w-7 h-7 rounded-lg grid place-items-center ${c.tint}`}>
          <span aria-hidden className="text-[12px]">◆</span>
        </div>
        <div className="text-[11px] tracking-[0.18em] uppercase text-ink-tertiary">{label}</div>
      </div>
      <div className="text-3xl font-bold tabular flex items-baseline gap-1.5">
        {value}
        {valueSuffix && (
          <span className="text-sm text-ink-tertiary font-medium">{valueSuffix}</span>
        )}
      </div>
      <div className="flex items-center gap-2 text-xs">
        <span className={[
          'font-semibold',
          delta.dir === 'up' ? 'text-growth-green' : 'text-growth-red',
        ].join(' ')}>
          {delta.dir === 'up' ? '▲' : '▼'} {delta.text}
        </span>
        <span className="text-ink-tertiary">{sub}</span>
      </div>
      <Sparkline data={sparkline} color={c.stroke} gradientId={`spark-${id}`} />
    </div>
  );
}

function Sparkline({ data, color, gradientId }) {
  if (!data.length) return null;
  const w = 200, h = 40;
  const step = w / (data.length - 1);
  const pts = data.map((y, i) => `${i * step} ${y}`).join(' L');
  const path = `M${pts}`;
  const fill = `M${pts} L${w} ${h} L0 ${h} Z`;
  return (
    <svg className="mt-auto -mx-1" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" width="100%" height="40">
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity="0.3" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={fill} fill={`url(#${gradientId})`} />
      <path d={path} stroke={color} strokeWidth="2" fill="none" />
    </svg>
  );
}
