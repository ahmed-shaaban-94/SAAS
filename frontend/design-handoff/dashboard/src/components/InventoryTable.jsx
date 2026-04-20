import React from 'react';
import { inventory } from '../data/mock.js';

const pillCls = {
  critical: 'bg-growth-red/15 text-growth-red',
  low:      'bg-chart-amber/15 text-chart-amber',
  healthy:  'bg-growth-green/15 text-growth-green',
};

const dosToneCls = {
  critical: 'text-growth-red',
  low: 'text-chart-amber',
  healthy: 'text-growth-green',
};

export default function InventoryTable() {
  const [filter, setFilter] = React.useState('All branches');
  const filters = ['All branches', 'Maadi', 'Heliopolis', 'Giza'];

  return (
    <div className="rounded-card bg-card border border-border/40 p-6">
      <header className="flex flex-wrap items-center gap-3 mb-3">
        <h3 className="text-[15px] font-semibold">Inventory — reorder watchlist</h3>
        <span className="font-mono text-[11px] text-ink-tertiary">sorted by days-of-stock</span>
        <div className="ml-auto flex gap-1">
          {filters.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={[
                'px-2.5 py-1 rounded-full text-[12px] border transition',
                filter === f
                  ? 'bg-accent/15 text-accent-strong border-accent/40'
                  : 'bg-transparent text-ink-secondary border-border/40 hover:text-ink-primary',
              ].join(' ')}
            >
              {f}
            </button>
          ))}
        </div>
      </header>

      <table className="w-full text-[13px]">
        <thead>
          <tr className="text-[11px] uppercase tracking-wider text-ink-tertiary">
            <th className="text-left font-medium py-2">Product</th>
            <th className="text-left font-medium py-2">SKU</th>
            <th className="text-right font-medium py-2">On-hand</th>
            <th className="text-right font-medium py-2">Days of stock</th>
            <th className="text-right font-medium py-2">Velocity</th>
            <th className="text-left font-medium py-2">Status</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {inventory.map((row) => (
            <tr key={row.sku} className="border-t border-border/30">
              <td className="py-3 font-medium">{row.name}</td>
              <td className="py-3 font-mono text-ink-tertiary">{row.sku}</td>
              <td className="py-3 tabular text-right">{row.onHand}</td>
              <td className={`py-3 tabular text-right font-semibold ${dosToneCls[row.status]}`}>{row.daysOfStock}d</td>
              <td className="py-3 tabular text-right">{row.velocity} / day</td>
              <td className="py-3">
                <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wider ${pillCls[row.status]}`}>
                  {row.status === 'critical' ? 'Critical' : row.status === 'low' ? 'Low' : 'Healthy'}
                </span>
              </td>
              <td className="py-3 text-right">
                {row.status === 'healthy' ? (
                  <a href="#" className="text-ink-tertiary text-[12.5px]">Watch</a>
                ) : (
                  <a href="#" className="text-accent-strong text-[12.5px] font-semibold">Reorder →</a>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
