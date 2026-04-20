import React from 'react';

const nav = [
  {
    section: 'Overview',
    items: [
      { label: 'Dashboard', active: true },
      { label: 'Explorer' },
      { label: 'Forecasts' },
    ],
  },
  {
    section: 'Operations',
    items: [
      { label: 'Inventory' },
      { label: 'Branches' },
      { label: 'Suppliers' },
      { label: 'Expiry' },
    ],
  },
  {
    section: 'Data',
    items: [
      { label: 'Pipelines' },
      { label: 'Sources' },
      { label: 'Models' },
    ],
  },
];

export default function Sidebar() {
  return (
    <aside className="sticky top-0 h-screen overflow-y-auto border-r border-border/50 bg-page/40 p-5">
      <div className="flex items-center gap-2.5 pb-4 mb-4 border-b border-border/40">
        <div className="w-8 h-8 rounded-[9px] grid place-items-center text-page font-bold
                        bg-gradient-to-br from-accent to-chart-purple shadow-[0_6px_16px_rgba(0,199,242,0.35)]">
          DP
        </div>
        <div className="text-[15px] font-bold tracking-tight">DataPulse</div>
      </div>

      {nav.map((group) => (
        <div key={group.section}>
          <div className="text-[10.5px] tracking-[0.22em] uppercase text-ink-tertiary px-3 pt-3.5 pb-2">
            {group.section}
          </div>
          {group.items.map((i) => (
            <a
              key={i.label}
              href="#"
              className={[
                'flex items-center gap-2.5 px-3 py-2 rounded-[10px] text-[13.5px] my-px transition',
                i.active
                  ? 'bg-gradient-to-r from-accent/[0.12] to-accent/0 text-ink-primary shadow-[inset_2px_0_0_#00c7f2]'
                  : 'text-ink-secondary hover:bg-white/[0.04] hover:text-ink-primary',
              ].join(' ')}
            >
              <span className="w-4 h-4 rounded-sm bg-white/10" aria-hidden />
              {i.label}
            </a>
          ))}
        </div>
      ))}
    </aside>
  );
}
