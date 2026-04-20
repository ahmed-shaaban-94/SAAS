import React from 'react';
import { pipeline } from '../data/mock.js';

const dotCls = {
  ok:      'bg-growth-green',
  running: 'bg-chart-amber animate-pulse',
  pending: 'bg-ink-tertiary',
};

export default function PipelineHealth() {
  return (
    <div className="rounded-card bg-card border border-border/40 p-6">
      <header className="flex items-center gap-3 mb-3">
        <h3 className="text-[15px] font-semibold">Pipeline health</h3>
        <span className="font-mono text-[11px] text-ink-tertiary">medallion · last run</span>
      </header>

      <div className="flex items-stretch gap-2">
        {pipeline.nodes.map((n, i) => (
          <React.Fragment key={n.label}>
            <div className={[
              'flex-1 rounded-xl border px-3 py-2.5 relative',
              n.status === 'running'
                ? 'border-chart-amber/40 bg-chart-amber/[0.06]'
                : 'border-border/40 bg-elevated/40',
            ].join(' ')}>
              <div className="text-[10.5px] uppercase tracking-[0.18em] text-ink-tertiary">{n.label}</div>
              <div className="text-[13px] font-semibold mt-0.5">{n.value}</div>
              <span className={`absolute top-2.5 right-2.5 w-2 h-2 rounded-full ${dotCls[n.status]}`} />
            </div>
            {i < pipeline.nodes.length - 1 && (
              <div className="self-center text-ink-tertiary">→</div>
            )}
          </React.Fragment>
        ))}
      </div>

      <div className="mt-4 flex flex-col gap-3 text-[12.5px]">
        <Row label="Last full run" value={`${pipeline.lastRun.at} · ${pipeline.lastRun.duration}`} />
        <Row label="Quality gates passed" value={pipeline.gates} tone="green" />
        <Row label="dbt tests" value={pipeline.tests} tone="green" />
        <Row label="Next scheduled run" value={pipeline.nextRun} />
      </div>

      <div className="mt-4">
        <div className="text-[10.5px] tracking-[0.18em] uppercase text-ink-tertiary mb-2.5">Run history · 7d</div>
        <div className="flex items-end gap-1 h-12">
          {pipeline.history.map((h, i) => {
            const warn = i === pipeline.warningIndex;
            return (
              <div
                key={i}
                className="flex-1 rounded-[3px]"
                style={{
                  height: `${h}%`,
                  background: warn
                    ? 'linear-gradient(180deg, #ffab3d, rgba(255,171,61,0.3))'
                    : 'linear-gradient(180deg, #1dd48b, rgba(29,212,139,0.3))',
                }}
                title={warn ? 'warning' : 'healthy'}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}

function Row({ label, value, tone }) {
  const toneCls =
    tone === 'green' ? 'text-growth-green' : 'text-ink-primary';
  return (
    <div className="flex justify-between">
      <span className="text-ink-secondary">{label}</span>
      <span className={`tabular font-semibold ${toneCls}`}>{value}</span>
    </div>
  );
}
