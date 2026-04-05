"use client";

import { useTopStaff } from "@/hooks/use-top-staff";
import { useFilters } from "@/contexts/filter-context";
import { formatCurrency, formatCompact } from "@/lib/formatters";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { Trophy, Medal, Crown, Award } from "lucide-react";
import Link from "next/link";

const MEDAL_COLORS = ["#FFD700", "#C0C0C0", "#CD7F32"]; // Gold, Silver, Bronze
const MEDAL_BG = ["bg-yellow-500/10", "bg-gray-400/10", "bg-orange-700/10"];
const MEDAL_ICONS = [Crown, Medal, Award];

export function GamifiedLeaderboard() {
  const { filters } = useFilters();
  const { data, isLoading } = useTopStaff(filters);

  if (isLoading) return <LoadingCard className="h-96" />;
  if (!data?.items?.length)
    return <EmptyState title="No staff data available" />;

  const maxValue = data.items[0]?.value || 1;

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="mb-6 flex items-center gap-2">
        <Trophy className="h-5 w-5 text-accent" />
        <h3 className="text-sm font-semibold text-text-primary">
          Staff Leaderboard
        </h3>
        <span className="ml-auto text-xs text-text-secondary">
          Total: {formatCurrency(data.total)}
        </span>
      </div>

      {/* Top 3 Podium */}
      {data.items.length >= 3 && (
        <div className="mb-8 flex items-end justify-center gap-4 px-4">
          {/* 2nd Place */}
          <div className="flex w-28 flex-col items-center">
            <div
              className="mb-2 flex h-12 w-12 items-center justify-center rounded-full"
              style={{ backgroundColor: MEDAL_COLORS[1] + "20" }}
            >
              <Medal className="h-6 w-6" style={{ color: MEDAL_COLORS[1] }} />
            </div>
            <span className="w-full truncate text-center text-xs font-medium text-text-primary">
              {data.items[1].name}
            </span>
            <span className="text-[10px] text-text-secondary">
              {formatCompact(data.items[1].value)}
            </span>
            <div
              className="mt-2 flex h-16 w-full items-end justify-center rounded-t-lg"
              style={{ backgroundColor: MEDAL_COLORS[1] + "15" }}
            >
              <span
                className="mb-2 text-lg font-bold"
                style={{ color: MEDAL_COLORS[1] }}
              >
                2
              </span>
            </div>
          </div>

          {/* 1st Place */}
          <div className="flex w-32 flex-col items-center">
            <div
              className="mb-2 flex h-14 w-14 items-center justify-center rounded-full ring-2 ring-yellow-400/50"
              style={{ backgroundColor: MEDAL_COLORS[0] + "20" }}
            >
              <Crown className="h-7 w-7" style={{ color: MEDAL_COLORS[0] }} />
            </div>
            <span className="w-full truncate text-center text-sm font-bold text-text-primary">
              {data.items[0].name}
            </span>
            <span className="text-xs font-medium text-accent">
              {formatCompact(data.items[0].value)}
            </span>
            <div
              className="mt-2 flex h-24 w-full items-end justify-center rounded-t-lg"
              style={{ backgroundColor: MEDAL_COLORS[0] + "15" }}
            >
              <span
                className="mb-2 text-2xl font-bold"
                style={{ color: MEDAL_COLORS[0] }}
              >
                1
              </span>
            </div>
          </div>

          {/* 3rd Place */}
          <div className="flex w-28 flex-col items-center">
            <div
              className="mb-2 flex h-12 w-12 items-center justify-center rounded-full"
              style={{ backgroundColor: MEDAL_COLORS[2] + "20" }}
            >
              <Award className="h-6 w-6" style={{ color: MEDAL_COLORS[2] }} />
            </div>
            <span className="w-full truncate text-center text-xs font-medium text-text-primary">
              {data.items[2].name}
            </span>
            <span className="text-[10px] text-text-secondary">
              {formatCompact(data.items[2].value)}
            </span>
            <div
              className="mt-2 flex h-12 w-full items-end justify-center rounded-t-lg"
              style={{ backgroundColor: MEDAL_COLORS[2] + "15" }}
            >
              <span
                className="mb-2 text-lg font-bold"
                style={{ color: MEDAL_COLORS[2] }}
              >
                3
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Full Rankings List */}
      <div className="space-y-2">
        {data.items.map((item, i) => {
          const barWidth = (item.value / maxValue) * 100;
          const isTop3 = i < 3;
          const MedalIcon = isTop3 ? MEDAL_ICONS[i] : null;

          return (
            <Link
              key={item.key}
              href={`/staff/${item.key}`}
              className={`group flex items-center gap-3 rounded-lg px-3 py-2 transition-all hover:bg-divider/50 ${
                isTop3 ? MEDAL_BG[i] : ""
              }`}
            >
              {/* Rank */}
              <div className="w-7 flex-shrink-0 text-center">
                {isTop3 && MedalIcon ? (
                  <MedalIcon
                    className="mx-auto h-4 w-4"
                    style={{ color: MEDAL_COLORS[i] }}
                  />
                ) : (
                  <span className="text-sm font-medium text-text-secondary">
                    #{item.rank}
                  </span>
                )}
              </div>

              {/* Name + Progress Bar */}
              <div className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-text-primary transition-colors group-hover:text-accent">
                  {item.name}
                </span>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-divider">
                  <div
                    className="h-full rounded-full transition-all duration-1000 ease-out"
                    style={{
                      width: `${barWidth}%`,
                      backgroundColor: isTop3 ? MEDAL_COLORS[i] : "#D97706",
                      opacity: isTop3 ? 1 : 0.6,
                    }}
                  />
                </div>
              </div>

              {/* Value */}
              <div className="flex-shrink-0 text-right">
                <span className="text-sm font-bold text-text-primary">
                  {formatCompact(item.value)}
                </span>
                <span className="block text-[10px] text-text-secondary">
                  {item.pct_of_total.toFixed(1)}%
                </span>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
