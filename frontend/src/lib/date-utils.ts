import { format, subDays, startOfMonth, startOfYear } from "date-fns";

/**
 * Parse integer date key (e.g., 20240115, "20240115", or "2024-01-15") to display string.
 * Accepts both string and number since parseDecimals may convert integer strings to numbers.
 */
export function parseDateKey(key: string | number): string {
  const k = String(key);
  // Handle "YYYY-MM-DD" format
  if (k.includes("-") && k.length === 10) {
    const d = new Date(key + "T00:00:00Z");
    return format(d, "MMM dd");
  }
  // Handle integer key like "20240115"
  if (/^\d{8}$/.test(k)) {
    const year = k.slice(0, 4);
    const month = k.slice(4, 6);
    const day = k.slice(6, 8);
    const d = new Date(`${year}-${month}-${day}T00:00:00Z`);
    return format(d, "MMM dd");
  }
  return k;
}

export function formatDateParam(date: Date): string {
  return format(date, "yyyy-MM-dd");
}

export function formatDateLabel(value: string | Date): string {
  const date = typeof value === "string" ? new Date(`${value}T00:00:00`) : value;
  return format(date, "MMM dd, yyyy");
}

export interface DatePreset {
  label: string;
  startDate: Date;
  endDate: Date;
}

export function getDatePresets(referenceDate?: Date): DatePreset[] {
  const anchor = referenceDate ?? new Date();
  return [
    { label: "Last 7 days", startDate: subDays(anchor, 7), endDate: anchor },
    { label: "Last 30 days", startDate: subDays(anchor, 30), endDate: anchor },
    { label: "Last 90 days", startDate: subDays(anchor, 90), endDate: anchor },
    { label: "Month to date", startDate: startOfMonth(anchor), endDate: anchor },
    { label: "Year to date", startDate: startOfYear(anchor), endDate: anchor },
  ];
}
