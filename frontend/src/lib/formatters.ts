/**
 * Format currency for Egyptian pharmaceutical sales context.
 * Uses "ar-EG" locale with EGP currency — outputs "١٬٢٣٤ ج.م.‏" natively,
 * but we use "en-u-nu-latn" numbering to keep Latin digits (1,234 EGP)
 * since the pharma sales data itself uses Latin numerals.
 */
export function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) return "N/A";
  return new Intl.NumberFormat("ar-EG-u-nu-latn", {
    style: "currency",
    currency: "EGP",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "N/A";
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return "N/A";
  return new Intl.NumberFormat("ar-EG-u-nu-latn").format(value);
}

export function truncate(str: string, maxLen: number = 20): string {
  return str.length > maxLen ? str.slice(0, maxLen) + "..." : str;
}

export function formatCompact(value: number | null | undefined): string {
  if (value === null || value === undefined) return "N/A";
  if (Math.abs(value) >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    return `${(value / 1_000).toFixed(0)}K`;
  }
  return value.toFixed(0);
}

export function formatDuration(seconds: number | null): string {
  if (seconds == null) return "-";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
}
