"use client";

import { memo, useMemo, useState } from "react";
import { useHeatmap } from "@/hooks/use-heatmap";
import { formatCurrency } from "@/lib/formatters";
import { LoadingCard } from "@/components/loading-card";

function getColor(value: number, min: number, max: number, isDark: boolean): string {
  if (max === min) return isDark ? "var(--divider)" : "var(--divider)";
  const ratio = (value - min) / (max - min);
  // Use opacity-based approach with growth-green for consistent theming
  const base = isDark ? [52, 211, 153] : [5, 150, 105]; // emerald shades
  const opacity = 0.2 + ratio * 0.8;
  return `rgba(${base[0]}, ${base[1]}, ${base[2]}, ${opacity})`;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DAYS = ["Mon", "", "Wed", "", "Fri", "", ""];

export const CalendarHeatmap = memo(function CalendarHeatmap() {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const { data, isLoading } = useHeatmap(year);
  const [hoveredCell, setHoveredCell] = useState<{
    date: string;
    value: number;
    x: number;
    y: number;
  } | null>(null);

  const isDark =
    typeof document !== "undefined" &&
    document.documentElement.classList.contains("dark");

  const grid = useMemo(() => {
    if (!data?.cells.length) return [];

    const cellMap = new Map(data.cells.map((c) => [c.date, c.value]));

    // Build weeks grid (53 weeks x 7 days)
    const startDate = new Date(year, 0, 1);
    const startDay = startDate.getDay(); // 0=Sun
    const weeks: { date: string; value: number; dayOfWeek: number }[][] = [];
    let currentWeek: { date: string; value: number; dayOfWeek: number }[] = [];

    // Pad first week
    for (let i = 0; i < (startDay === 0 ? 6 : startDay - 1); i++) {
      currentWeek.push({ date: "", value: -1, dayOfWeek: i });
    }

    const endDate = new Date(year, 11, 31);
    const current = new Date(startDate);

    while (current <= endDate) {
      const dateStr = current.toISOString().split("T")[0];
      const dow = current.getDay();
      const adjustedDow = dow === 0 ? 6 : dow - 1; // Mon=0

      currentWeek.push({
        date: dateStr,
        value: cellMap.get(dateStr) ?? 0,
        dayOfWeek: adjustedDow,
      });

      if (adjustedDow === 6) {
        weeks.push(currentWeek);
        currentWeek = [];
      }

      current.setDate(current.getDate() + 1);
    }

    if (currentWeek.length > 0) weeks.push(currentWeek);
    return weeks;
  }, [data, year]);

  if (isLoading) return <LoadingCard className="h-48" />;

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text-primary">Revenue Heatmap</h3>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setYear((y) => y - 1)}
            className="rounded px-2 py-0.5 text-xs text-text-secondary hover:bg-divider"
            aria-label={`Previous year (${year - 1})`}
          >
            &larr;
          </button>
          <span className="w-10 text-center text-xs font-medium text-text-primary" aria-live="polite">
            {year}
          </span>
          <button
            onClick={() => setYear((y) => Math.min(y + 1, currentYear))}
            disabled={year >= currentYear}
            className="rounded px-2 py-0.5 text-xs text-text-secondary hover:bg-divider disabled:opacity-30"
            aria-label={`Next year (${Math.min(year + 1, currentYear)})`}
          >
            &rarr;
          </button>
        </div>
      </div>

      {/* Month labels */}
      <div className="mb-1 ml-8 flex gap-0">
        {MONTHS.map((m) => (
          <span
            key={m}
            className="text-[9px] text-text-secondary"
            style={{ width: `${100 / 12}%` }}
          >
            {m}
          </span>
        ))}
      </div>

      <div className="flex gap-1">
        {/* Day labels */}
        <div className="flex flex-col gap-[3px] pr-1">
          {DAYS.map((d, i) => (
            <span
              key={i}
              className="h-[11px] text-[9px] leading-[11px] text-text-secondary"
            >
              {d}
            </span>
          ))}
        </div>

        {/* Grid */}
        <div className="relative flex flex-1 gap-[3px] overflow-hidden">
          {grid.map((week, wi) => (
            <div key={wi} className="flex flex-col gap-[3px]">
              {week.map((cell, ci) => (
                <div
                  key={ci}
                  className="h-[11px] w-[11px] cursor-pointer rounded-[2px] transition-all duration-150 hover:ring-1 hover:ring-accent"
                  style={{
                    backgroundColor:
                      cell.value < 0
                        ? "transparent"
                        : getColor(
                            cell.value,
                            data?.min_value ?? 0,
                            data?.max_value ?? 1,
                            isDark,
                          ),
                  }}
                  onMouseEnter={(e) => {
                    if (cell.date) {
                      const rect = e.currentTarget.getBoundingClientRect();
                      setHoveredCell({
                        date: cell.date,
                        value: cell.value,
                        x: rect.left,
                        y: rect.top,
                      });
                    }
                  }}
                  onMouseLeave={() => setHoveredCell(null)}
                />
              ))}
            </div>
          ))}

          {/* Tooltip */}
          {hoveredCell && (
            <div
              className="pointer-events-none fixed z-50 rounded-md bg-card border border-border px-2 py-1 text-xs text-text-primary shadow-lg"
              style={{ left: hoveredCell.x - 40, top: hoveredCell.y - 36 }}
            >
              <span className="font-medium">
                {formatCurrency(hoveredCell.value)}
              </span>
              <span className="ml-1 text-text-secondary">{hoveredCell.date}</span>
            </div>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="mt-2 flex items-center justify-end gap-1">
        <span className="text-[9px] text-text-secondary">Less</span>
        {[0.1, 0.3, 0.6, 0.9].map((r) => (
          <div
            key={r}
            className="h-[11px] w-[11px] rounded-[2px]"
            style={{
              backgroundColor: getColor(r * 100, 0, 100, isDark),
            }}
          />
        ))}
        <span className="text-[9px] text-text-secondary">More</span>
      </div>
    </div>
  );
});
