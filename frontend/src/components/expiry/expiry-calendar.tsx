"use client";

import { useEffect, useMemo, useState } from "react";
import {
  addMonths,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameMonth,
  isToday,
  parseISO,
  startOfMonth,
  startOfWeek,
  subMonths,
} from "date-fns";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useFilters } from "@/contexts/filter-context";
import { EmptyState } from "@/components/empty-state";
import { ErrorRetry } from "@/components/error-retry";
import { LoadingCard } from "@/components/loading-card";
import { Button } from "@/components/ui/button";
import { useExpiryCalendar } from "@/hooks/use-expiry-calendar";
import { cn } from "@/lib/utils";

const dayColorMap: Record<string, string> = {
  expired: "border-growth-red/40 bg-growth-red/10 text-growth-red",
  critical: "border-chart-amber/40 bg-chart-amber/10 text-chart-amber",
  warning: "border-yellow-400/40 bg-yellow-400/10 text-yellow-500",
  caution: "border-accent/30 bg-accent/10 text-accent",
  safe: "border-growth-green/30 bg-growth-green/10 text-growth-green",
};

export function ExpiryCalendar() {
  const { filters } = useFilters();
  const { data, error, isLoading, mutate } = useExpiryCalendar(filters);
  const [month, setMonth] = useState(() => startOfMonth(new Date()));

  useEffect(() => {
    if (data?.[0]?.date) {
      setMonth(startOfMonth(parseISO(data[0].date)));
    }
  }, [data]);

  const calendarDays = useMemo(() => {
    const start = startOfWeek(startOfMonth(month), { weekStartsOn: 1 });
    const end = endOfWeek(endOfMonth(month), { weekStartsOn: 1 });
    return eachDayOfInterval({ start, end });
  }, [month]);

  const daysByDate = useMemo(() => {
    return new Map((data ?? []).map((item) => [item.date, item]));
  }, [data]);

  if (isLoading) return <LoadingCard lines={8} className="h-[30rem]" />;
  if (error) {
    return (
      <ErrorRetry
        title="Failed to load expiry calendar"
        description="Calendar data could not be loaded."
        onRetry={() => mutate()}
      />
    );
  }
  if (!data?.length) {
    return (
      <EmptyState
        title="No expiry calendar data"
        description="Upcoming expiries will appear here when batches are available."
      />
    );
  }

  return (
    <section className="viz-panel rounded-[1.75rem] p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
            Expiry Calendar
          </p>
          <h3 className="mt-2 text-2xl font-bold tracking-tight text-text-primary">
            {format(month, "MMMM yyyy")}
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => setMonth((value) => subMonths(value, 1))}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" onClick={() => setMonth((value) => addMonths(value, 1))}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-7 gap-2 text-center text-xs font-semibold uppercase tracking-[0.18em] text-text-secondary">
        {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((label) => (
          <div key={label} className="py-2">{label}</div>
        ))}
      </div>

      <div className="mt-2 grid grid-cols-7 gap-2">
        {calendarDays.map((day) => {
          const key = format(day, "yyyy-MM-dd");
          const entry = daysByDate.get(key);
          const classes = entry ? dayColorMap[entry.alert_level] ?? dayColorMap.safe : "border-border/70 bg-page text-text-secondary";

          return (
            <div
              key={key}
              className={cn(
                "min-h-24 rounded-2xl border p-2 text-left transition-colors",
                classes,
                !isSameMonth(day, month) && "opacity-45",
                isToday(day) && "ring-1 ring-accent",
              )}
            >
              <div className="flex items-center justify-between text-sm font-semibold">
                <span>{format(day, "d")}</span>
                {entry && <span className="rounded-full bg-card/70 px-2 py-0.5 text-[10px] font-bold">{entry.batch_count}</span>}
              </div>
              <div className="mt-4 space-y-1">
                <p className="text-xs uppercase tracking-wide">{entry ? entry.alert_level : "No expiries"}</p>
                {entry && (
                  <p className="text-xs">
                    {entry.total_quantity} units expiring
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
