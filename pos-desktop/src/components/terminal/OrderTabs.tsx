import { Plus } from "lucide-react";
import { cn } from "@shared/lib/utils";

interface OrderTabsProps {
  orderName: string;
  itemCount: number;
}

// Visual stub for multi-cart tabs — Gemini POV port (2026-04-30).
// The cart store does not yet support parallel orders, so the `+`
// button is rendered disabled with a tooltip. Wire to real state
// once `usePosCart` exposes parallel orders.
// TODO(multi-cart): wire `+` and tab clicks once usePosCart supports parallel orders.
export function OrderTabs({ orderName, itemCount }: OrderTabsProps) {
  return (
    <div
      className="flex gap-1 overflow-x-auto pb-1"
      role="tablist"
      aria-label="Active orders"
    >
      <button
        type="button"
        role="tab"
        aria-selected="true"
        data-testid="order-tab-active"
        className={cn(
          "group relative flex min-w-[140px] items-center gap-2 rounded-t-xl px-4 py-2",
          "border-t-2 text-sm font-bold transition-all",
          "bg-[var(--pos-card)] text-[var(--pos-accent-from)]",
          "border-[var(--pos-tab-active-border)]",
          "shadow-[0_-4px_10px_-2px_rgba(0,0,0,0.05)]",
        )}
      >
        <span className="flex-1 truncate text-right">{orderName}</span>
        <span
          data-testid="order-tab-count"
          className={cn(
            "rounded-full px-1.5 py-0.5 text-[10px] font-mono",
            "bg-[rgb(var(--pos-glow-indigo)/0.10)] text-[var(--pos-accent-from)]",
          )}
        >
          {itemCount}
        </span>
      </button>
      <button
        type="button"
        disabled
        data-testid="order-tab-add"
        title="Multi-cart coming soon"
        aria-label="Add new order (coming soon)"
        className={cn(
          "rounded-t-xl px-3 py-2 transition-opacity",
          "bg-[var(--pos-line)] text-[var(--pos-ink-3)]",
          "opacity-50 cursor-not-allowed",
        )}
      >
        <Plus size={18} aria-hidden="true" />
      </button>
    </div>
  );
}
