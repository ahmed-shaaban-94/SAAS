import { useMemo } from "react";
import { CreditCard } from "lucide-react";
import { cn } from "@shared/lib/utils";
import type { TilePaymentMethod } from "./types";
import { fmtEgp } from "./types";

export interface InsuranceState {
  name: string;
  coveragePct: number;
  nationalId: string;
}

interface ActivePaymentStripProps {
  method: TilePaymentMethod;
  grandTotal: number;
  // Cash
  cashTendered: string;
  onCashTenderedChange: (v: string) => void;
  // Card
  cardLast4?: string;
  onCardLast4Change?: (v: string) => void;
  // Insurance
  insurance: InsuranceState | null;
  onInsuranceChange: (next: InsuranceState | null) => void;
  insurers?: string[];
  /** Optional — when provided, the Insurance strip renders a "Configure" button
   * that opens the redesigned InsuranceModal for a richer picker (PR 6). */
  onOpenInsuranceModal?: () => void;
  // Voucher
  voucherCode: string | null;
  voucherDiscount: number;
  onOpenVoucherModal: () => void;
}

/** Egyptian pound denominations for cash change breakdown. */
const EGP_DENOMINATIONS = [200, 100, 50, 20, 10, 5, 1] as const;

const DEFAULT_INSURERS = [
  "Med-Net",
  "Al-Ahly Egypt",
  "Axa Egypt",
  "Misr Insurance",
  "Gulf Takaful",
];

/**
 * Context-sensitive strip that sits below the payment tiles. Its
 * contents change based on the active payment method:
 *   - cash:      tendered + change + EGP denomination breakdown
 *   - card:      pinpad status + optional last-4 field
 *   - insurance: insurer dropdown + national ID + coverage + split
 *   - voucher:   applied code + discount + "Change code" button
 */
export function ActivePaymentStrip(props: ActivePaymentStripProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-[var(--pos-line)] bg-black/20 p-3",
        "min-h-[96px]",
      )}
      data-testid="active-payment-strip"
    >
      {props.method === "cash" && (
        <CashStrip
          grandTotal={props.grandTotal}
          tendered={props.cashTendered}
          onChange={props.onCashTenderedChange}
        />
      )}
      {props.method === "card" && (
        <CardStrip
          last4={props.cardLast4 ?? ""}
          onLast4Change={props.onCardLast4Change ?? (() => {})}
        />
      )}
      {props.method === "insurance" && (
        <InsuranceStrip
          grandTotal={props.grandTotal}
          insurance={props.insurance}
          onChange={props.onInsuranceChange}
          insurers={props.insurers ?? DEFAULT_INSURERS}
          onOpenModal={props.onOpenInsuranceModal}
        />
      )}
      {props.method === "voucher" && (
        <VoucherStrip
          code={props.voucherCode}
          discount={props.voucherDiscount}
          onOpen={props.onOpenVoucherModal}
        />
      )}
    </div>
  );
}

function CashStrip({
  grandTotal,
  tendered,
  onChange,
}: {
  grandTotal: number;
  tendered: string;
  onChange: (v: string) => void;
}) {
  const tenderedNum = parseFloat(tendered) || 0;
  const change = Math.max(0, tenderedNum - grandTotal);
  const ok = tenderedNum >= grandTotal && grandTotal > 0;

  const breakdown = useMemo(() => {
    let remaining = Math.round(change);
    const out: Array<[number, number]> = [];
    for (const d of EGP_DENOMINATIONS) {
      const n = Math.floor(remaining / d);
      if (n > 0) {
        out.push([d, n]);
        remaining -= n * d;
      }
    }
    return out;
  }, [change]);

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="font-mono text-[10px] font-bold uppercase tracking-wider text-text-secondary">
            Tendered
          </div>
          <input
            type="text"
            inputMode="decimal"
            value={tendered}
            onChange={(e) => onChange(e.target.value.replace(/[^\d.]/g, ""))}
            placeholder="0.00"
            aria-label="Cash tendered"
            data-pos-scanner-ignore=""
            data-testid="cash-tendered-input"
            className={cn(
              "mt-0.5 w-full bg-transparent font-mono text-[22px] font-bold tabular-nums",
              ok ? "text-text-primary" : "text-amber-300",
              "placeholder:text-text-secondary focus:outline-none",
            )}
          />
        </div>
        <div className="text-right">
          <div className="font-mono text-[10px] font-bold uppercase tracking-wider text-text-secondary">
            Change
          </div>
          <div
            className={cn(
              "mt-0.5 font-mono text-[22px] font-bold tabular-nums",
              change > 0 ? "text-emerald-400" : "text-text-secondary",
            )}
          >
            EGP {fmtEgp(change)}
          </div>
        </div>
      </div>
      {breakdown.length > 0 && (
        <div className="flex flex-wrap gap-1 border-t border-dashed border-[var(--pos-line)] pt-1.5">
          {breakdown.map(([d, n]) => (
            <span
              key={d}
              className={cn(
                "rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold tabular-nums",
                "border border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
              )}
            >
              {n}×{d}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function CardStrip({
  last4,
  onLast4Change,
}: {
  last4: string;
  onLast4Change: (v: string) => void;
}) {
  return (
    <div className="flex items-center gap-3">
      <div className="grid h-10 w-10 place-items-center rounded-lg border border-cyan-400/30 bg-cyan-400/10 text-cyan-300">
        <CreditCard className="h-5 w-5" aria-hidden="true" />
      </div>
      <div className="flex-1">
        <div className="text-sm font-semibold text-text-primary">Tap or swipe card</div>
        <div className="font-mono text-[10.5px] text-text-secondary">
          Pinpad · <span className="text-emerald-400">READY</span>
        </div>
      </div>
      <input
        type="text"
        inputMode="numeric"
        maxLength={4}
        value={last4}
        onChange={(e) => onLast4Change(e.target.value.replace(/\D/g, "").slice(0, 4))}
        placeholder="Last 4"
        aria-label="Card last 4 digits"
        data-pos-scanner-ignore=""
        className={cn(
          "w-24 rounded-md border border-border bg-surface-raised px-2 py-1",
          "font-mono text-sm tracking-widest text-text-primary placeholder:text-text-secondary",
          "focus:border-cyan-400/50 focus:outline-none",
        )}
      />
    </div>
  );
}

function InsuranceStrip({
  grandTotal,
  insurance,
  onChange,
  insurers,
  onOpenModal,
}: {
  grandTotal: number;
  insurance: InsuranceState | null;
  onChange: (next: InsuranceState | null) => void;
  insurers: string[];
  onOpenModal?: () => void;
}) {
  const insurerPays = insurance ? (grandTotal * insurance.coveragePct) / 100 : 0;
  const customerPays = Math.max(0, grandTotal - insurerPays);

  return (
    <div className="space-y-2">
      {onOpenModal && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={onOpenModal}
            data-testid="insurance-configure-button"
            className={cn(
              "rounded-md border px-2.5 py-1 text-[11px] font-semibold",
              "border-[var(--pos-purple)]/60 bg-[var(--pos-purple)]/10",
              "text-violet-300 hover:bg-[var(--pos-purple)]/15",
            )}
          >
            Configure…
          </button>
        </div>
      )}
      <div className="grid grid-cols-2 gap-3">
        <label className="block">
          <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-text-secondary">
            Insurer
          </span>
          <select
            value={insurance?.name ?? ""}
            onChange={(e) => {
              const name = e.target.value;
              if (!name) {
                onChange(null);
              } else {
                onChange({
                  name,
                  coveragePct: insurance?.coveragePct ?? 80,
                  nationalId: insurance?.nationalId ?? "",
                });
              }
            }}
            aria-label="Select insurer"
            data-pos-scanner-ignore=""
            data-testid="insurance-insurer-select"
            className={cn(
              "mt-0.5 w-full rounded-md border border-border bg-surface-raised px-2 py-1",
              "text-sm text-text-primary focus:outline-none",
            )}
          >
            <option value="">— Select —</option>
            {insurers.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-text-secondary">
            National ID
          </span>
          <input
            type="text"
            inputMode="numeric"
            value={insurance?.nationalId ?? ""}
            onChange={(e) => {
              if (!insurance) return;
              onChange({ ...insurance, nationalId: e.target.value.replace(/\D/g, "").slice(0, 14) });
            }}
            placeholder="14 digits"
            aria-label="National ID"
            disabled={!insurance}
            data-pos-scanner-ignore=""
            className={cn(
              "mt-0.5 w-full rounded-md border border-border bg-surface-raised px-2 py-1",
              "font-mono text-sm text-text-primary placeholder:text-text-secondary",
              "focus:outline-none disabled:opacity-40",
            )}
          />
        </label>
      </div>
      <div className="flex items-center justify-between border-t border-dashed border-[var(--pos-line)] pt-2 text-[12.5px]">
        <span className="text-text-secondary">
          {insurance
            ? `${insurance.name} · ${insurance.coveragePct}% coverage`
            : "Select an insurer to split the bill"}
        </span>
        {insurance && (
          <span className="font-mono font-semibold text-violet-300 tabular-nums">
            Customer EGP {fmtEgp(customerPays)} · Insurer EGP {fmtEgp(insurerPays)}
          </span>
        )}
      </div>
    </div>
  );
}

function VoucherStrip({
  code,
  discount,
  onOpen,
}: {
  code: string | null;
  discount: number;
  onOpen: () => void;
}) {
  if (!code) {
    return (
      <div className="flex items-center justify-between text-[12.5px] text-text-secondary">
        <span>Press F7 or tap Voucher to enter a code</span>
        <button
          type="button"
          onClick={onOpen}
          className="rounded-md border border-amber-400/40 bg-amber-400/10 px-3 py-1 text-amber-300 hover:bg-amber-400/15"
        >
          Enter code
        </button>
      </div>
    );
  }
  return (
    <div className="flex items-center justify-between">
      <div>
        <div className="font-mono text-[10px] font-bold uppercase tracking-wider text-amber-400">
          Voucher valid
        </div>
        <div className="font-mono text-[13px] font-semibold text-text-primary">{code}</div>
      </div>
      <div className="flex items-center gap-3">
        <span className="font-mono text-[20px] font-bold tabular-nums text-amber-300">
          −EGP {fmtEgp(discount)}
        </span>
        <button
          type="button"
          onClick={onOpen}
          className="rounded-md border border-border bg-surface-raised px-3 py-1 text-[12px] text-text-primary hover:border-cyan-400/40"
        >
          Change code
        </button>
      </div>
    </div>
  );
}
