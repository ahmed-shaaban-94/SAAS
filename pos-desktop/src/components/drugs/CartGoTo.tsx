import { useNavigate } from "react-router-dom";
import { ShoppingCart } from "lucide-react";
import { cn } from "@shared/lib/utils";

interface Props {
  itemCount: number;
  grandTotal: number;
}

export function CartGoTo({ itemCount, grandTotal }: Props) {
  const navigate = useNavigate();
  const hasItems = itemCount > 0;
  return (
    <button
      type="button"
      onClick={() => navigate("/terminal")}
      data-testid="cart-goto-button"
      className={cn(
        "mt-auto grid grid-cols-[auto_1fr_auto] items-center gap-2.5 rounded-xl px-3.5 py-3 text-start",
        hasItems
          ? "border border-emerald-400/40 bg-emerald-400/10 text-emerald-300"
          : "border border-border bg-white/[0.03] text-text-secondary",
      )}
    >
      <ShoppingCart className="h-4.5 w-4.5" aria-hidden="true" />
      <div>
        <div className="text-[12.5px] font-bold">
          {hasItems
            ? `In cart: ${itemCount} item${itemCount === 1 ? "" : "s"}`
            : "Cart is empty"}
        </div>
        <div className="mt-0.5 font-mono text-[9.5px] uppercase tracking-[0.18em] text-text-secondary">
          F1 to terminal
        </div>
      </div>
      <span className="font-mono text-[13px] font-bold tabular-nums">
        {formatEGP(grandTotal)}
      </span>
    </button>
  );
}

function formatEGP(value: number): string {
  return `EGP ${value.toFixed(2)}`;
}
