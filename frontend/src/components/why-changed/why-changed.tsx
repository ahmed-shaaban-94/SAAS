"use client";

/**
 * Why-Changed — waterfall decomposition of a metric delta.
 *
 * Click any number in the dashboard, get a modal with the drivers that
 * moved it. Each driver is shown as a symmetric bar centred on zero:
 *   - Negative contributions extend left (red)
 *   - Positive contributions extend right (green)
 *   - Bar width is proportional to |contribution| / max(|contribution|)
 *
 * Data model is intentionally simple and static-first so the feature can
 * ship before a /why-changed endpoint lands. The static decompositions
 * live in `why-changed-data.ts` keyed by metric. A future PR replaces
 * the static lookup with a real fetch without changing this component.
 */

import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import "./why-changed.css";

export interface WhyChangedDriver {
  label: string;
  contribution: number; // signed; same unit as the total delta
  /** Optional short note explaining the driver (tooltip / accessibility). */
  note?: string;
}

export interface WhyChangedData {
  /** Shown as the eyebrow — e.g. "Why did Maadi revenue drop 18%?" */
  title: string;
  subtitle?: string;
  /** Label for the total delta row (top of modal). */
  totalLabel: string;
  /** Pre-formatted value for display (e.g. "−EGP 107K" or "+3.2%"). */
  totalDisplay: string;
  /** Sign of the total — determines coloring of the total value. */
  totalSign: "up" | "dn" | "flat";
  drivers: WhyChangedDriver[];
  /** 0–1; shown as a "confidence" pill in the footer. */
  confidence?: number;
  /** Optional deep-link target for "See full breakdown" action. */
  actionHref?: string;
  actionLabel?: string;
}

interface WhyChangedProps {
  open: boolean;
  onClose: () => void;
  data: WhyChangedData;
}

export function WhyChanged({ open, onClose, data }: WhyChangedProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dlg = dialogRef.current;
    if (!dlg) return;
    if (open && !dlg.open) {
      dlg.showModal();
    } else if (!open && dlg.open) {
      dlg.close();
    }
  }, [open]);

  useEffect(() => {
    const dlg = dialogRef.current;
    if (!dlg) return;
    const onCancel = (e: Event) => {
      e.preventDefault();
      onClose();
    };
    dlg.addEventListener("cancel", onCancel);
    return () => dlg.removeEventListener("cancel", onCancel);
  }, [onClose]);

  // Normalise bar widths to the largest absolute contribution.
  const maxAbs = Math.max(1, ...data.drivers.map((d) => Math.abs(d.contribution)));

  return (
    <dialog
      ref={dialogRef}
      className="wc-dialog why-changed-root"
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose();
      }}
      aria-label={data.title}
    >
      <div className="wc-head">
        <div className="wc-title-group">
          <div className="wc-eyebrow">Why did this change?</div>
          <h3>{data.title}</h3>
          {data.subtitle && <div className="wc-sub">{data.subtitle}</div>}
        </div>
        <button type="button" className="wc-close" onClick={onClose} aria-label="Close">
          <X size={14} />
        </button>
      </div>

      <div className="wc-body">
        <div className="wc-total">
          <span className="wc-total-label">{data.totalLabel}</span>
          <span className={`wc-total-value ${data.totalSign === "flat" ? "" : data.totalSign}`}>
            {data.totalDisplay}
          </span>
        </div>

        <div className="wc-drivers" role="list">
          {data.drivers.map((d) => {
            const widthPct = (Math.abs(d.contribution) / maxAbs) * 50;
            const fillClass = d.contribution < 0 ? "neg" : "pos";
            const valueClass = d.contribution < 0 ? "neg" : "pos";
            const sign = d.contribution < 0 ? "" : "+";
            return (
              <div key={d.label} className="wc-driver" role="listitem" title={d.note}>
                <span className="wc-driver-label">{d.label}</span>
                <div className="wc-driver-bar">
                  <span className="zero" />
                  <span className={`fill ${fillClass}`} style={{ width: `${widthPct}%` }} />
                </div>
                <span className={`wc-driver-value ${valueClass}`}>
                  {sign}
                  {formatContribution(d.contribution)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="wc-foot">
        {data.confidence != null && (
          <span className="wc-confidence">
            CONFIDENCE {Math.round(data.confidence * 100)}%
          </span>
        )}
        <span className="spacer" />
        {data.actionHref ? (
          <a
            className="wc-action"
            href={data.actionHref}
            onClick={() => onClose()}
            style={{ textDecoration: "none", display: "inline-block" }}
          >
            {data.actionLabel ?? "See full breakdown"}
          </a>
        ) : (
          <button type="button" className="wc-action" onClick={onClose}>
            Got it
          </button>
        )}
      </div>
    </dialog>
  );
}

function formatContribution(v: number): string {
  const abs = Math.abs(v);
  if (abs >= 1_000_000) return `${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${(abs / 1_000).toFixed(0)}K`;
  if (abs % 1 === 0) return String(Math.round(abs));
  return abs.toFixed(1);
}
