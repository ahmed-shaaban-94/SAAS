"use client";

import { TrendingUp } from "lucide-react";
import type { ChannelsBreakdown, ChannelShare } from "@/types/api";

interface ChannelDonutProps {
  data?: ChannelsBreakdown;
  loading?: boolean;
}

const COLOR_BY_CHANNEL: Record<ChannelShare["channel"], string> = {
  retail: "#20bce5",
  wholesale: "#7467f8",
  institution: "#ffab3d",
  online: "#1dd48b",
};

export function ChannelDonut({ data, loading }: ChannelDonutProps) {
  const R = 48;
  const C = 2 * Math.PI * R;
  const items = data?.items ?? [];
  let runningOffset = 0;
  const segments = items.map((it) => {
    const len = (it.pct_of_total / 100) * C;
    const seg = { ...it, dash: `${len} ${C}`, offset: runningOffset };
    runningOffset -= len;
    return seg;
  });

  const totalLabel = data ? formatTotal(data.total_egp) : "—";
  const online = items.find((i) => i.channel === "online");

  return (
    <div className="rounded-[14px] bg-card border border-border/40 p-6 flex flex-col">
      <header className="flex items-center gap-3 mb-3">
        <h3 className="text-[15px] font-semibold">Channel split</h3>
        <span className="font-mono text-[11px] text-ink-tertiary">month-to-date</span>
      </header>

      {loading ? (
        <div className="h-36 bg-elevated/30 rounded animate-pulse" aria-busy="true" />
      ) : items.length === 0 ? (
        <p className="text-sm text-ink-tertiary py-4">No channel data available.</p>
      ) : (
        <div className="flex items-center gap-5 py-1">
          <svg
            width="140"
            height="140"
            viewBox="0 0 120 120"
            className="shrink-0"
            role="img"
            aria-label="Channel split donut"
          >
            <g transform="rotate(-90 60 60)">
              {segments.map((s) => (
                <circle
                  key={s.channel}
                  cx="60"
                  cy="60"
                  r={R}
                  fill="none"
                  stroke={COLOR_BY_CHANNEL[s.channel]}
                  strokeWidth="18"
                  strokeDasharray={s.dash}
                  strokeDashoffset={s.offset}
                >
                  <title>{`${s.label}: ${s.pct_of_total.toFixed(1)}%`}</title>
                </circle>
              ))}
            </g>
            <text x="60" y="58" textAnchor="middle" fill="var(--text-primary)" fontSize="18" fontWeight="700">
              {totalLabel}
            </text>
            <text x="60" y="74" textAnchor="middle" fill="var(--text-tertiary)" fontSize="9" letterSpacing="1.5">
              TOTAL EGP
            </text>
          </svg>

          <ul className="flex-1 space-y-2">
            {items.map((ch) => (
              <li key={ch.channel} className="flex items-center gap-2.5 text-[13px]">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ background: COLOR_BY_CHANNEL[ch.channel] }}
                  aria-hidden
                />
                <span className="text-ink-secondary flex-1 truncate">{ch.label}</span>
                <span className="w-20 h-1 rounded-full bg-border/40 overflow-hidden" aria-hidden>
                  <span
                    className="block h-full"
                    style={{
                      background: COLOR_BY_CHANNEL[ch.channel],
                      width: `${ch.pct_of_total}%`,
                    }}
                  />
                </span>
                <span className="tabular-nums text-ink-primary font-semibold w-12 text-right">
                  {ch.pct_of_total.toFixed(0)}%
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {online && (
        <div className="mt-4 pt-3 border-t border-border/35 text-[12.5px] text-ink-secondary flex items-center gap-2">
          <TrendingUp className="w-3.5 h-3.5 text-growth-green" aria-hidden />
          Online channel at <b className="text-growth-green">{online.pct_of_total.toFixed(0)}%</b>
          {" "}of total — fastest-growing segment.
        </div>
      )}
      {data?.data_coverage === "partial" && (
        <p className="mt-2 text-[11px] text-ink-tertiary">
          Some channels are derived from customer-type heuristics — partial coverage.
        </p>
      )}
    </div>
  );
}

function formatTotal(total: number): string {
  if (total >= 1_000_000) return `${(total / 1_000_000).toFixed(2)}M`;
  if (total >= 1_000) return `${(total / 1_000).toFixed(0)}K`;
  return `${total.toFixed(0)}`;
}
