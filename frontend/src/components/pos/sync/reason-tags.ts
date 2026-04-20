/**
 * Client-side classification of a rejected-queue `last_error` string into a
 * colored reason tag for the Sync Issues UI. The backend does not return a
 * machine-readable reason code yet — this lives in the frontend so the
 * operator sees a glanceable tag without waiting on an API change.
 */
export type ReasonKey =
  | "PRICE_MISMATCH"
  | "EXPIRED_VOUCHER"
  | "STOCK_NEGATIVE"
  | "INSURANCE_REJECT"
  | "DUPLICATE_BARCODE"
  | "UNKNOWN";

export type ReasonTone = "amber" | "red" | "purple" | "neutral";

export interface ReasonMeta {
  key: ReasonKey;
  label: string;
  tone: ReasonTone;
}

export const REASON_META: Record<ReasonKey, ReasonMeta> = {
  PRICE_MISMATCH: { key: "PRICE_MISMATCH", label: "PRICE_MISMATCH", tone: "amber" },
  EXPIRED_VOUCHER: { key: "EXPIRED_VOUCHER", label: "EXPIRED_VOUCHER", tone: "amber" },
  STOCK_NEGATIVE: { key: "STOCK_NEGATIVE", label: "STOCK_NEGATIVE", tone: "red" },
  INSURANCE_REJECT: { key: "INSURANCE_REJECT", label: "INSURANCE_REJECT", tone: "red" },
  DUPLICATE_BARCODE: { key: "DUPLICATE_BARCODE", label: "DUPLICATE_BARCODE", tone: "purple" },
  UNKNOWN: { key: "UNKNOWN", label: "UNKNOWN", tone: "neutral" },
};

export function classifyReason(lastError: string | null): ReasonMeta {
  const e = (lastError ?? "").toLowerCase();
  if (!e) return REASON_META.UNKNOWN;
  if (e.includes("price") || e.includes("amount mismatch") || e.includes("total mismatch")) {
    return REASON_META.PRICE_MISMATCH;
  }
  if (e.includes("voucher") || e.includes("promo") || e.includes("expired code")) {
    return REASON_META.EXPIRED_VOUCHER;
  }
  if (e.includes("stock") || e.includes("negative inventory") || e.includes("oversold")) {
    return REASON_META.STOCK_NEGATIVE;
  }
  if (e.includes("insurance") || e.includes("insurer") || e.includes("authorization denied")) {
    return REASON_META.INSURANCE_REJECT;
  }
  if (e.includes("duplicate") || e.includes("barcode") || e.includes("already")) {
    return REASON_META.DUPLICATE_BARCODE;
  }
  return REASON_META.UNKNOWN;
}

export const TONE_CLASSES: Record<
  ReasonTone,
  { rail: string; chip: string; text: string; dot: string }
> = {
  amber: {
    rail: "bg-amber-400",
    chip: "border-amber-400/40 bg-amber-400/10 text-amber-300",
    text: "text-amber-300",
    dot: "bg-amber-400",
  },
  red: {
    rail: "bg-destructive",
    chip: "border-destructive/40 bg-destructive/10 text-destructive",
    text: "text-destructive",
    dot: "bg-destructive",
  },
  purple: {
    rail: "bg-purple-400",
    chip: "border-purple-400/40 bg-purple-400/10 text-purple-300",
    text: "text-purple-300",
    dot: "bg-purple-400",
  },
  neutral: {
    rail: "bg-text-secondary/60",
    chip: "border-border bg-surface-raised text-text-secondary",
    text: "text-text-secondary",
    dot: "bg-text-secondary/60",
  },
};
