import { useEffect, useRef, useState } from "react";
import { Loader2, Ticket } from "lucide-react";
import { ModalShell } from "@pos/components/ModalShell";
import { useVoucherValidate } from "@shared/hooks/use-voucher-validate";
import { computeVoucherDiscount, type CartVoucher } from "@pos/lib/voucher";
import { cn } from "@shared/lib/utils";

/**
 * VoucherCodeModal — redesigned for PR 6 (Voucher + Promo + Insurance).
 *
 * Design source: docs/design/pos-terminal/frames/pos/modals.jsx § VoucherModal.
 * Contract preserved from Phase 1b (#463) so existing cart context / terminal
 * integration / Vitest expectations keep working:
 *   - Accessible label "Voucher code" on the input
 *   - Primary button "Validate code" → server validates → flips to "Apply voucher"
 *   - onApply emits a full CartVoucher with resolved discount in EGP
 */
export interface VoucherCodeModalProps {
  open: boolean;
  cartSubtotal: number;
  onApply: (voucher: CartVoucher) => void;
  onCancel: () => void;
  /** Initial code to prefill (e.g. from keypad). */
  initialCode?: string;
}

const QUICK_CODES = ["RAMADAN25", "NEW100", "LOYALTY10"] as const;
const CODE_PATTERN = /[^A-Z0-9_-]/g;

function fmtEgp(n: number): string {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function normalizeCode(raw: string): string {
  return raw.toUpperCase().replace(CODE_PATTERN, "");
}

export function VoucherCodeModal({
  open,
  cartSubtotal,
  onApply,
  onCancel,
  initialCode = "",
}: VoucherCodeModalProps) {
  const [code, setCode] = useState(initialCode);
  const inputRef = useRef<HTMLInputElement>(null);
  const validator = useVoucherValidate();

  useEffect(() => {
    if (open) {
      setCode(initialCode);
      validator.reset();
      setTimeout(() => inputRef.current?.focus(), 80);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, initialCode]);

  async function handleValidate() {
    const normalized = normalizeCode(code);
    if (!normalized) return;
    try {
      await validator.validate(normalized, cartSubtotal);
    } catch {
      // validator.error surfaces below
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validator.data) {
      handleValidate();
      return;
    }
    const resolved = computeVoucherDiscount(
      validator.data.discount_type,
      Number(validator.data.value),
      cartSubtotal,
    );
    onApply({
      code: validator.data.code,
      discount_type: validator.data.discount_type,
      value: Number(validator.data.value),
      discount: resolved,
    });
  }

  const preview = validator.data;
  const resolvedDiscount = preview
    ? computeVoucherDiscount(
        preview.discount_type,
        Number(preview.value),
        cartSubtotal,
      )
    : 0;

  const borderStatus: "idle" | "valid" | "invalid" = validator.error
    ? "invalid"
    : preview
      ? "valid"
      : "idle";

  return (
    <ModalShell
      open={open}
      onClose={onCancel}
      title="Apply voucher"
      subtitle="Enter the discount code supplied to the customer."
      badge="VOUCHER"
      accent="amber"
      width={520}
      testId="pos-voucher-modal"
      titleId="pos-voucher-modal-title"
      icon={<Ticket className="h-5 w-5" aria-hidden="true" />}
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label className="sr-only" htmlFor="pos-voucher-code-input">
          Voucher code
        </label>
        <div className="group relative flex gap-2">
          {/* Gradient-blur focus halo (Gemini POV upgrade). Sits behind the
              input + button row; intensifies on focus-within. Decorative only. */}
          <span
            aria-hidden="true"
            className={cn(
              "pointer-events-none absolute -inset-1 rounded-xl blur-md",
              "bg-gradient-to-r from-amber-400/30 via-amber-300/20 to-amber-400/30",
              "opacity-0 transition-opacity duration-300",
              "group-focus-within:opacity-100",
            )}
          />
          <input
            id="pos-voucher-code-input"
            ref={inputRef}
            data-pos-scanner-ignore=""
            data-testid="pos-voucher-code-input"
            value={code}
            onChange={(e) => {
              setCode(normalizeCode(e.target.value));
              if (validator.data || validator.error) validator.reset();
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                if (preview) {
                  handleSubmit(e as unknown as React.FormEvent);
                } else {
                  handleValidate();
                }
              }
            }}
            placeholder="RAMADAN25"
            aria-label="Voucher code"
            autoComplete="off"
            inputMode="text"
            className="relative font-mono"
            style={{
              flex: 1,
              fontSize: 18,
              fontWeight: 600,
              letterSpacing: "0.08em",
              padding: "14px 14px",
              background: "rgba(0,0,0,0.3)",
              border: "1.5px solid",
              borderColor:
                borderStatus === "invalid"
                  ? "var(--pos-red, #ff7b7b)"
                  : borderStatus === "valid"
                    ? "var(--pos-green, #1dd48b)"
                    : "var(--pos-line, rgba(255,255,255,0.06))",
              borderRadius: 10,
              direction: "ltr",
              color: "var(--pos-ink, #e8ecf2)",
            }}
          />
          <button
            type="button"
            onClick={handleValidate}
            disabled={validator.isLoading || code.trim().length === 0}
            className="relative font-semibold"
            data-testid="pos-voucher-validate-button"
            style={{
              padding: "0 18px",
              borderRadius: 10,
              background: "rgba(255,171,61,0.18)",
              border: "1px solid var(--pos-amber, #ffab3d)",
              color: "var(--pos-amber, #ffab3d)",
              fontSize: 13,
              opacity: code.trim().length === 0 ? 0.45 : 1,
              cursor:
                validator.isLoading || code.trim().length === 0
                  ? "not-allowed"
                  : "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            {validator.isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
            Validate
          </button>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {QUICK_CODES.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => {
                setCode(q);
                validator.reset();
              }}
              className="font-mono"
              style={{
                fontSize: 10,
                padding: "3px 8px",
                borderRadius: 5,
                background: "rgba(184,192,204,0.06)",
                border:
                  "1px solid var(--pos-line, rgba(255,255,255,0.06))",
                color: "var(--pos-ink-3, #7a8494)",
                letterSpacing: "0.08em",
              }}
            >
              {q}
            </button>
          ))}
        </div>

        {validator.error && !preview && (
          <div
            role="alert"
            data-testid="pos-voucher-error"
            style={{
              marginTop: 4,
              padding: 12,
              borderRadius: 10,
              background: "rgba(255,123,123,0.08)",
              border: "1px solid rgba(255,123,123,0.3)",
              color: "var(--pos-red, #ff7b7b)",
              fontSize: 12.5,
              fontWeight: 500,
            }}
          >
            {validator.error}
          </div>
        )}

        {preview && (
          <div
            data-testid="pos-voucher-preview"
            style={{
              marginTop: 4,
              background: "rgba(29,212,139,0.06)",
              border: "1px solid rgba(29,212,139,0.35)",
              borderRadius: 12,
              padding: 14,
              display: "flex",
              flexDirection: "column",
              gap: 10,
            }}
          >
            <div className="flex items-center gap-2">
              <span
                aria-hidden="true"
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: "var(--pos-green, #1dd48b)",
                }}
              />
              <span
                className="font-mono"
                style={{
                  fontSize: 10,
                  letterSpacing: "0.2em",
                  color: "var(--pos-green, #1dd48b)",
                  textTransform: "uppercase",
                  fontWeight: 700,
                }}
              >
                Voucher valid
              </span>
            </div>
            <div
              style={{
                fontFamily: "var(--font-fraunces), Fraunces, serif",
                fontSize: 17,
                fontStyle: "italic",
                color: "var(--pos-ink, #e8ecf2)",
              }}
            >
              {preview.discount_type === "percent"
                ? `${Number(preview.value)}% off`
                : `Flat EGP ${fmtEgp(Number(preview.value))} off`}
            </div>
            <div
              className="flex items-baseline justify-between"
              style={{
                paddingTop: 8,
                borderTop:
                  "1px dashed var(--pos-line, rgba(255,255,255,0.06))",
              }}
            >
              <span
                className="font-mono"
                style={{
                  fontSize: 10,
                  letterSpacing: "0.18em",
                  color: "var(--pos-ink-3, #7a8494)",
                  textTransform: "uppercase",
                }}
              >
                Voucher off
              </span>
              <span
                className="font-mono tabular-nums"
                data-testid="pos-voucher-resolved"
                style={{
                  fontSize: 24,
                  fontWeight: 700,
                  color: "var(--pos-amber, #ffab3d)",
                }}
              >
                −EGP {fmtEgp(resolvedDiscount)}
              </span>
            </div>
            <div
              className="font-mono"
              style={{
                fontSize: 10,
                color: "var(--pos-ink-3, #7a8494)",
              }}
            >
              {preview.code} · {preview.remaining_uses} use
              {preview.remaining_uses === 1 ? "" : "s"} left
            </div>
          </div>
        )}

        <div className="mt-2 flex gap-2">
          <button
            type="button"
            onClick={onCancel}
            className={cn(
              "flex-1 rounded-xl border px-4 py-3 text-[13px] font-semibold",
            )}
            style={{
              background: "transparent",
              borderColor: "var(--pos-line, rgba(255,255,255,0.06))",
              color: "var(--pos-ink-2, #b8c0cc)",
            }}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={validator.isLoading || code.trim().length === 0}
            data-testid="pos-voucher-submit"
            className="flex-[2] rounded-xl px-4 py-3 text-[13px] font-bold"
            style={{
              background: preview
                ? "linear-gradient(180deg, var(--pos-amber, #ffab3d), #e08f20)"
                : "rgba(255,255,255,0.04)",
              color: preview ? "#1a0c00" : "var(--pos-ink-4, #3f4a5a)",
              border: preview
                ? "none"
                : "1px solid var(--pos-line, rgba(255,255,255,0.06))",
              cursor:
                validator.isLoading || code.trim().length === 0
                  ? "not-allowed"
                  : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 10,
            }}
          >
            {validator.isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
            {preview ? "Apply voucher" : "Validate code"}
          </button>
        </div>
      </form>
    </ModalShell>
  );
}
