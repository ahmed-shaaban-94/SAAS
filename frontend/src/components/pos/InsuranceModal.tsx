"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { ModalShell } from "@/components/pos/ModalShell";
import type { InsuranceState } from "@/components/pos/terminal/ActivePaymentStrip";

/**
 * InsuranceModal — redesigned for PR 6.
 *
 * Design source: docs/design/pos-terminal/frames/pos/modals.jsx § InsuranceModal.
 *
 * Flow:
 *   1. Cashier picks an insurer from a 2-col grid (default coverage % suggested)
 *   2. Enters national ID (14 digits; paste-friendly)
 *   3. Optionally overrides coverage % via slider
 *   4. Optional pre-authorisation number
 *   5. Confirm → onApply({ name, coveragePct, nationalId })
 *      matching the existing InsuranceState contract in ActivePaymentStrip.
 *
 * The pre-auth string is returned via onApplyExtras so the terminal page can
 * persist `insurance_no` into the pending checkout payload without pulling
 * the inline picker apart.
 */
export interface InsurerOption {
  id: string;
  name: string;
  /** Suggested default coverage percentage (0-100). */
  coverage: number;
}

export interface InsuranceApplyPayload {
  state: InsuranceState;
  insuranceNumber: string | null;
  insurerId: string;
}

export interface InsuranceModalProps {
  open: boolean;
  onClose: () => void;
  onApply: (payload: InsuranceApplyPayload) => void;
  /** Cart total (VAT-inclusive) — used to compute the patient / insurer split. */
  grandTotal: number;
  /** Ordered insurer picker list. Defaults to the design-frame set. */
  insurers?: InsurerOption[];
  /** Optional pre-fill if the cashier already chose an insurer inline. */
  initial?: Partial<InsuranceState> | null;
}

const DEFAULT_INSURERS: InsurerOption[] = [
  { id: "mednet", name: "Med-Net", coverage: 80 },
  { id: "axa", name: "Axa Egypt", coverage: 70 },
  { id: "alahly", name: "Al-Ahly Egypt", coverage: 85 },
  { id: "allianz", name: "Allianz Egypt", coverage: 75 },
  { id: "bupa", name: "Bupa Egypt", coverage: 90 },
  { id: "misr", name: "Misr Life", coverage: 60 },
];

function fmtEgp(n: number): string {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function sanitizeNationalId(raw: string): string {
  return raw.replace(/\D/g, "").slice(0, 14);
}

export function InsuranceModal({
  open,
  onClose,
  onApply,
  grandTotal,
  insurers = DEFAULT_INSURERS,
  initial,
}: InsuranceModalProps) {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [nationalId, setNationalId] = useState("");
  const [coverage, setCoverage] = useState<number>(insurers[0]?.coverage ?? 80);
  const [preauth, setPreauth] = useState("");
  const nationalIdRef = useRef<HTMLInputElement>(null);

  // When opened, reset from `initial` (if any) or defaults.
  useEffect(() => {
    if (!open) return;
    const matched = initial?.name
      ? Math.max(
          0,
          insurers.findIndex((i) => i.name === initial.name),
        )
      : 0;
    const idx = matched < 0 ? 0 : matched;
    setSelectedIdx(idx);
    setNationalId(initial?.nationalId ?? "");
    setCoverage(initial?.coveragePct ?? insurers[idx]?.coverage ?? 80);
    setPreauth("");
    // Focus synchronously after mount — useEffect already runs post-DOM-commit,
    // so the ref is populated. The previous setTimeout(80) raced with
    // userEvent.type in tests: when the test typed into preauth, the late
    // setTimeout would shift focus back to national-id mid-type, causing
    // characters to land in the wrong field.
    nationalIdRef.current?.focus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Switching insurer explicitly resets coverage to the insurer's default.
  // (The open-time init effect above has already honoured `initial.coveragePct`
  // when the modal mounts, so we intentionally do NOT re-run on `selectedIdx`
  // changes from the init effect — only from user clicks.)
  function handleSelectInsurer(i: number) {
    setSelectedIdx(i);
    const insurer = insurers[i];
    if (insurer) setCoverage(insurer.coverage);
  }

  const selectedInsurer = insurers[selectedIdx];
  const insurerPays = useMemo(
    () => (grandTotal * coverage) / 100,
    [grandTotal, coverage],
  );
  const patientPays = Math.max(0, grandTotal - insurerPays);

  const canApply =
    Boolean(selectedInsurer) &&
    nationalId.length === 14 &&
    coverage >= 0 &&
    coverage <= 100;

  function handleApply() {
    if (!canApply || !selectedInsurer) return;
    onApply({
      state: {
        name: selectedInsurer.name,
        coveragePct: coverage,
        nationalId,
      },
      insuranceNumber: preauth.trim() ? preauth.trim() : null,
      insurerId: selectedInsurer.id,
    });
    onClose();
  }

  return (
    <ModalShell
      open={open}
      onClose={onClose}
      title="Medical insurance"
      subtitle="Split the bill between the insurer and the patient."
      badge="INSURANCE"
      accent="purple"
      width={560}
      testId="pos-insurance-modal"
      titleId="pos-insurance-modal-title"
      icon={<ShieldCheck className="h-5 w-5" aria-hidden="true" />}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleApply();
        }}
        className="flex flex-col gap-3.5"
      >
        {/* Insurer grid */}
        <div>
          <div
            className="font-mono"
            style={{
              fontSize: 9.5,
              fontWeight: 700,
              letterSpacing: "0.2em",
              color: "var(--pos-ink-3, #7a8494)",
              textTransform: "uppercase",
              marginBottom: 7,
            }}
          >
            Insurer
          </div>
          <div
            className="grid gap-1.5"
            style={{ gridTemplateColumns: "1fr 1fr" }}
            data-testid="pos-insurance-insurer-grid"
          >
            {insurers.map((ins, i) => {
              const active = i === selectedIdx;
              return (
                <button
                  key={ins.id}
                  type="button"
                  aria-pressed={active}
                  onClick={() => handleSelectInsurer(i)}
                  data-testid={`pos-insurance-insurer-${ins.id}`}
                  className="flex items-center justify-between text-start"
                  style={{
                    padding: "10px 12px",
                    borderRadius: 8,
                    background: active
                      ? "rgba(116,103,248,0.15)"
                      : "rgba(8,24,38,0.5)",
                    border: "1.5px solid",
                    borderColor: active
                      ? "var(--pos-purple, #7467f8)"
                      : "var(--pos-line, rgba(255,255,255,0.06))",
                    fontSize: 12.5,
                    fontWeight: 600,
                    color: "var(--pos-ink, #e8ecf2)",
                  }}
                >
                  <span className="truncate">{ins.name}</span>
                  <span
                    className="font-mono tabular-nums"
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      color: active
                        ? "var(--pos-purple, #7467f8)"
                        : "var(--pos-ink-3, #7a8494)",
                    }}
                  >
                    {ins.coverage}%
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* National ID + pre-auth */}
        <div className="grid gap-2.5" style={{ gridTemplateColumns: "1fr 1fr" }}>
          <Field label="National ID">
            <input
              ref={nationalIdRef}
              value={nationalId}
              onChange={(e) => setNationalId(sanitizeNationalId(e.target.value))}
              inputMode="numeric"
              autoComplete="off"
              placeholder="14 digits"
              data-pos-scanner-ignore=""
              data-testid="pos-insurance-national-id"
              aria-label="National ID"
              style={fieldInputStyle}
            />
          </Field>
          <Field label="Pre-auth">
            <input
              value={preauth}
              onChange={(e) => setPreauth(e.target.value.slice(0, 32))}
              placeholder="—"
              data-pos-scanner-ignore=""
              data-testid="pos-insurance-preauth"
              aria-label="Pre-authorisation number"
              style={fieldInputStyle}
            />
          </Field>
        </div>

        {/* Coverage slider */}
        <div>
          <div className="mb-1.5 flex justify-between">
            <span
              className="font-mono"
              style={{
                fontSize: 9.5,
                fontWeight: 700,
                letterSpacing: "0.2em",
                color: "var(--pos-ink-3, #7a8494)",
                textTransform: "uppercase",
              }}
            >
              Coverage
            </span>
            <span
              className="font-mono tabular-nums"
              data-testid="pos-insurance-coverage-value"
              style={{
                fontSize: 14,
                fontWeight: 700,
                color: "var(--pos-purple, #7467f8)",
              }}
            >
              {coverage}%
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={coverage}
            onChange={(e) => setCoverage(parseInt(e.target.value, 10) || 0)}
            aria-label="Coverage percentage"
            data-testid="pos-insurance-coverage-slider"
            style={{ width: "100%", accentColor: "#7467f8" }}
          />
        </div>

        {/* Computed portions */}
        <div
          className="grid gap-3.5 rounded-xl p-3.5"
          style={{
            gridTemplateColumns: "1fr 1fr",
            background: "rgba(116,103,248,0.06)",
            border: "1px solid rgba(116,103,248,0.3)",
          }}
        >
          <div>
            <div
              className="font-mono"
              style={{
                fontSize: 9.5,
                letterSpacing: "0.18em",
                color: "var(--pos-purple, #7467f8)",
                textTransform: "uppercase",
                fontWeight: 700,
                marginBottom: 4,
              }}
            >
              Insurer pays
            </div>
            <div
              className="font-mono tabular-nums"
              data-testid="pos-insurance-insurer-pays"
              style={{
                fontSize: 22,
                fontWeight: 700,
                color: "var(--pos-purple, #7467f8)",
              }}
            >
              EGP {fmtEgp(insurerPays)}
            </div>
          </div>
          <div>
            <div
              className="font-mono"
              style={{
                fontSize: 9.5,
                letterSpacing: "0.18em",
                color: "var(--pos-accent-hi, #5cdfff)",
                textTransform: "uppercase",
                fontWeight: 700,
                marginBottom: 4,
              }}
            >
              Patient pays
            </div>
            <div
              className="font-mono tabular-nums"
              data-testid="pos-insurance-patient-pays"
              style={{
                fontSize: 22,
                fontWeight: 700,
                color: "var(--pos-accent-hi, #5cdfff)",
                textShadow: "0 0 10px rgba(0,199,242,0.4)",
              }}
            >
              EGP {fmtEgp(patientPays)}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-xl px-4 py-3 text-[13px] font-semibold"
            style={{
              background: "transparent",
              border: "1px solid var(--pos-line, rgba(255,255,255,0.06))",
              color: "var(--pos-ink-2, #b8c0cc)",
            }}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!canApply}
            data-testid="pos-insurance-apply"
            className="flex-[2] rounded-xl px-4 py-3 text-[13px] font-bold"
            style={{
              background: canApply
                ? "linear-gradient(180deg, var(--pos-purple, #7467f8), #5a4fe0)"
                : "rgba(255,255,255,0.04)",
              color: canApply ? "#fff" : "var(--pos-ink-4, #3f4a5a)",
              border: canApply
                ? "none"
                : "1px solid var(--pos-line, rgba(255,255,255,0.06))",
              cursor: canApply ? "pointer" : "not-allowed",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 10,
            }}
          >
            Confirm
            <span
              className="font-mono"
              style={{
                fontSize: 10,
                background: "rgba(0,0,0,0.25)",
                border: "1px solid rgba(0,0,0,0.3)",
                borderRadius: 4,
                padding: "2px 5px",
                color: canApply ? "#fff" : "var(--pos-ink-4, #3f4a5a)",
              }}
            >
              Enter
            </span>
          </button>
        </div>
      </form>
    </ModalShell>
  );
}

const fieldInputStyle: React.CSSProperties = {
  width: "100%",
  fontSize: 14,
  fontWeight: 500,
  padding: "10px 10px",
  background: "rgba(0,0,0,0.3)",
  border: "1px solid var(--pos-line, rgba(255,255,255,0.06))",
  borderRadius: 8,
  letterSpacing: "0.04em",
  color: "var(--pos-ink, #e8ecf2)",
  fontFamily: "var(--font-jetbrains-mono), JetBrains Mono, monospace",
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span
        className="font-mono"
        style={{
          fontSize: 9.5,
          fontWeight: 700,
          letterSpacing: "0.2em",
          color: "var(--pos-ink-3, #7a8494)",
          textTransform: "uppercase",
        }}
      >
        {label}
      </span>
      {children}
    </label>
  );
}
