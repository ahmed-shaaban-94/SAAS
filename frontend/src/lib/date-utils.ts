import { format, subDays, startOfMonth, startOfYear } from "date-fns";

/**
 * Parse integer date key (e.g., "20240115" or "2024-01-15") to display string.
 */
export function parseDateKey(key: string): string {
  // Handle "YYYY-MM-DD" format
  if (key.includes("-") && key.length === 10) {
    const d = new Date(key + "T00:00:00Z");
    return format(d, "MMM dd");
  }
  // Handle integer key like "20240115"
  if (/^\d{8}$/.test(key)) {
    const year = key.slice(0, 4);
    const month = key.slice(4, 6);
    const day = key.slice(6, 8);
    const d = new Date(`${year}-${month}-${day}T00:00:00Z`);
    return format(d, "MMM dd");
  }
  return key;
}

export function formatDateParam(date: Date): string {
  return format(date, "yyyy-MM-dd");
}

export interface DatePreset {
  label: string;
  startDate: Date;
  endDate: Date;
}

export function getDatePresets(): DatePreset[] {
  const today = new Date();
  return [
    { label: "Last 7 days", startDate: subDays(today, 7), endDate: today },
    { label: "Last 30 days", startDate: subDays(today, 30), endDate: today },
    { label: "Last 90 days", startDate: subDays(today, 90), endDate: today },
    { label: "Month to date", startDate: startOfMonth(today), endDate: today },
    { label: "Year to date", startDate: startOfYear(today), endDate: today },
  ];
}
