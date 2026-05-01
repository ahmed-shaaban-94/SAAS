import { cn } from "@shared/lib/utils";
import { fmtEgp } from "./types";

interface TotalsHeroProps {
  subtotal: number;
  grandTotal: number;
  itemDiscountTotal: number;
  voucherDiscount: number;
  taxTotal: number;
  itemCount: number;
  voucherCode: string | null;
  insuranceCoveragePct: number | null;
}

interface ChipProps {
  label: string;
  value: string;
  tone?: "default" | "green" | "amber" | "purple";
}

const TONE_STYLES: Record<NonNullable<ChipProps["tone"]>, string> = {
  default: "border-[var(--pos-line)] bg-white/[0.04] text-text-primary",
  green: "border-emerald-400/40 bg-emerald-400/10 text-emerald-300",
  amber: "border-amber-400/40 bg-amber-400/10 text-amber-300",
  purple: "border-violet-400/40 bg-violet-400/10 text-violet-300",
};

function Chip({ label, value, tone = "default" }: ChipProps) {
  return (
    <span
      className={cn(
        "inline-flex items-baseline gap-1.5 rounded-full border px-2.5 py-1 text-[11px]",
        TONE_STYLES[tone],
      )}
    >
      <span className="font-mono text-[9px] font-bold uppercase tracking-wider">{label}</span>
      <span className="font-mono tabular-nums font-semibold">{value}</span>
    </span>
  );
}

/**
 * Totals Hero — the cashier's focal point. Giant Fraunces-italic grand
 * total with a cyan text-shadow glow, VAT/discount/voucher/coverage chips
 * underneath.
 */
export function TotalsHero({
  subtotal,
  grandTotal,
  itemDiscountTotal,
  voucherDiscount,
  taxTotal,
  itemCount,
  voucherCode,
  insuranceCoveragePct,
}: TotalsHeroProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl border border-cyan-400/35 p-4",
        "bg-gradient-to-b from-cyan-400/10 to-[rgba(22,52,82,0.4)]",
        "shadow-[0_0_0_1px_rgba(0,199,242,0.12),0_0_28px_rgba(0,199,242,0.1)]",
      )}
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(400px_200px_at_80%_-20%,rgba(0,199,242,0.15),transparent_60%)]"
      />

      <div className="relative flex items-baseline justify-between">
        <span className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-cyan-300">
          ● Total
        </span>
        <span className="font-mono text-[10px] uppercase tracking-wider text-text-secondary">
          {itemCount > 0 && (
            <>
              <span className="tabular-nums">{itemCount}</span> LN
            </>
          )}
        </span>
      </div>

      <div className="relative mt-1 flex items-baseline gap-2">
        {/* key={grandTotal} re-mounts the span on every value change so
            the existing `countUp` keyframe replays (motion-safe only). */}
        <span
          key={grandTotal}
          data-testid="totals-hero-grand"
          className={cn(
            "pos-display tabular-nums text-5xl text-text-primary",
            "motion-safe:animate-count-up",
          )}
        >
          {fmtEgp(grandTotal)}
        </span>
        <span className="font-mono text-sm font-semibold text-text-secondary">EGP</span>
      </div>

      <div className="relative mt-3 flex flex-wrap gap-1.5">
        <Chip label="Subtotal" value={fmtEgp(subtotal)} />
        {taxTotal > 0 && (
          <Chip label="VAT" value={fmtEgp(taxTotal)} />
        )}
        {itemDiscountTotal > 0 && (
          <Chip label="Discount" value={`−${fmtEgp(itemDiscountTotal)}`} tone="green" />
        )}
        {voucherDiscount > 0 && voucherCode && (
          <Chip
            label={`Voucher ${voucherCode}`}
            value={`−${fmtEgp(voucherDiscount)}`}
            tone="amber"
          />
        )}
        {insuranceCoveragePct !== null && insuranceCoveragePct > 0 && (
          <Chip label="Coverage" value={`${insuranceCoveragePct}%`} tone="purple" />
        )}
      </div>
    </div>
  );
}
