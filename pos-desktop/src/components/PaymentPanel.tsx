import { Banknote, CreditCard, Shield, Ticket } from "lucide-react";
import { cn } from "@shared/lib/utils";
import type { PaymentMethod } from "@pos/types/pos";

interface PaymentPanelProps {
  grandTotal: number;
  disabled?: boolean;
  onCheckout: (method: PaymentMethod) => void;
}

function fmt(n: number): string {
  return n.toLocaleString("ar-EG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

const PAYMENT_METHODS = [
  {
    method: "cash" as PaymentMethod,
    label: "CASH",
    shortcut: "F2",
    icon: Banknote,
    className: "bg-green-500/20 text-green-400 border-green-500/30 hover:bg-green-500/30",
  },
  {
    method: "card" as PaymentMethod,
    label: "CARD",
    shortcut: "",
    icon: CreditCard,
    className: "bg-blue-500/20 text-blue-400 border-blue-500/30 hover:bg-blue-500/30",
  },
  {
    method: "insurance" as PaymentMethod,
    label: "INSUR.",
    shortcut: "",
    icon: Shield,
    className: "bg-purple-500/20 text-purple-400 border-purple-500/30 hover:bg-purple-500/30",
  },
  {
    method: "voucher" as PaymentMethod,
    label: "VOUCHER",
    shortcut: "",
    icon: Ticket,
    className: "bg-amber-500/20 text-amber-400 border-amber-500/30 hover:bg-amber-500/30",
  },
] as const;

export function PaymentPanel({ grandTotal, disabled, onCheckout }: PaymentPanelProps) {
  return (
    <div className="space-y-3">
      <div className="rounded-xl border border-accent/20 bg-accent/5 p-3 text-center">
        <p className="text-xs font-medium uppercase tracking-wider text-text-secondary">
          Grand Total
        </p>
        <p className="mt-1 text-2xl font-bold tabular-nums text-accent">
          EGP {fmt(grandTotal)}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {PAYMENT_METHODS.map(({ method, label, shortcut, icon: Icon, className }) => (
          <button
            key={method}
            type="button"
            onClick={() => onCheckout(method)}
            disabled={disabled || grandTotal <= 0}
            aria-label={`Pay with ${label}${shortcut ? ` (${shortcut})` : ""}`}
            className={cn(
              // 64px min height for primary payment actions per plan spec
              "flex min-h-[4rem] flex-col items-center justify-center gap-1",
              "rounded-xl border font-semibold transition-all duration-100",
              "text-sm active:scale-95 disabled:pointer-events-none disabled:opacity-40",
              className,
            )}
          >
            <Icon className="h-5 w-5" />
            <span>{label}</span>
            {shortcut && (
              <span className="text-[10px] opacity-60">{shortcut}</span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
