"use client";

/**
 * Live Demo page — no authentication required.
 *
 * All data is simulated client-side using setInterval.  Inspired by Gemini's
 * posEngine pattern: KPI counters increment every second, the 30-day trend
 * chart scrolls in real time.
 *
 * No API calls are made — this page is fully self-contained and usable
 * before a user has signed in.
 */

import { useEffect, useRef, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { TrendingUp, Users, ShoppingCart, BarChart3, ArrowUpRight, Zap } from "lucide-react";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmt(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(Math.floor(n));
}

function fmtEGP(n: number): string {
  return `EGP ${fmt(n)}`;
}

/** Seeded pseudo-random that looks like realistic revenue. */
function baseRevenue(dayIndex: number): number {
  const base = 180_000;
  const weekly = Math.sin((dayIndex / 7) * Math.PI) * 35_000;
  const trend = dayIndex * 600;
  const noise = Math.sin(dayIndex * 2.4 + 1.7) * 12_000;
  return Math.max(50_000, base + weekly + trend + noise);
}

/** Build initial 30-day trend data. */
function buildTrend(offset = 0): { day: string; revenue: number }[] {
  return Array.from({ length: 30 }, (_, i) => ({
    day: `D${i + 1}`,
    revenue: Math.round(baseRevenue(i + offset)),
  }));
}

// ---------------------------------------------------------------------------
// KPI card
// ---------------------------------------------------------------------------
function DemoKPI({
  icon: Icon,
  label,
  value,
  delta,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  delta: string;
  color: string;
}) {
  return (
    <div
      className="flex flex-col gap-2 rounded-xl p-5"
      style={{ background: "#161B22", border: "1px solid #21262D" }}
    >
      <div className="flex items-center gap-2">
        <div
          className="flex h-8 w-8 items-center justify-center rounded-lg"
          style={{ background: `${color}15` }}
        >
          <Icon className="h-4 w-4" style={{ color }} />
        </div>
        <p className="text-xs font-medium" style={{ color: "#8B949E" }}>
          {label}
        </p>
      </div>
      <p className="text-2xl font-bold tabular-nums" style={{ color: "#E6EDF3" }}>
        {value}
      </p>
      <div className="flex items-center gap-1">
        <ArrowUpRight className="h-3.5 w-3.5" style={{ color: "#34D399" }} />
        <p className="text-xs font-semibold" style={{ color: "#34D399" }}>
          {delta}
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Custom tooltip for the area chart
// ---------------------------------------------------------------------------
function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { value: number }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div
      className="rounded-lg px-3 py-2 text-xs shadow-xl"
      style={{ background: "#1C2128", border: "1px solid #21262D", color: "#E6EDF3" }}
    >
      <p style={{ color: "#8B949E" }}>{label}</p>
      <p className="font-bold">{fmtEGP(payload[0].value)}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

const TICK_MS = 1_200; // how often KPIs tick up
const SCROLL_MS = 3_000; // how often the chart scrolls right

export default function DemoPage() {
  // State: raw counters that increment over time
  const [todayRevenue, setTodayRevenue] = useState(187_423);
  const [transactions, setTransactions] = useState(1_042);
  const [customers, setCustomers] = useState(783);
  const [avgBasket, setAvgBasket] = useState(179.9);

  // Trend chart data
  const [trend, setTrend] = useState(() => buildTrend(0));
  const dayOffsetRef = useRef(30);

  // KPI ticker — increment counters every TICK_MS ms
  useEffect(() => {
    const id = setInterval(() => {
      setTodayRevenue((v) => v + Math.round(Math.random() * 2_800 + 400));
      setTransactions((v) => v + Math.round(Math.random() * 3));
      setCustomers((v) => (Math.random() > 0.6 ? v + 1 : v));
      setAvgBasket((v) => +(v + (Math.random() - 0.45) * 0.8).toFixed(1));
    }, TICK_MS);
    return () => clearInterval(id);
  }, []);

  // Chart scroll — append a new day and drop the oldest every SCROLL_MS ms
  useEffect(() => {
    const id = setInterval(() => {
      dayOffsetRef.current += 1;
      const off = dayOffsetRef.current;
      setTrend((prev) => [
        ...prev.slice(1),
        { day: `D${off}`, revenue: Math.round(baseRevenue(off)) },
      ]);
    }, SCROLL_MS);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      {/* Hero banner */}
      <div className="rounded-xl p-6 sm:p-8" style={{ background: "#161B22", border: "1px solid #21262D" }}>
        <div className="flex items-start gap-3">
          <div
            className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl"
            style={{ background: "#6366F115" }}
          >
            <Zap className="h-5 w-5" style={{ color: "#6366F1" }} />
          </div>
          <div>
            <h1 className="text-lg font-bold sm:text-xl" style={{ color: "#E6EDF3" }}>
              DataPulse Live Demo
            </h1>
            <p className="mt-0.5 text-sm" style={{ color: "#8B949E" }}>
              Watching a simulated pharmacy chain in real time — KPIs update every
              1.2 seconds, trend chart scrolls every 3 seconds.
            </p>
          </div>
        </div>
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <DemoKPI
          icon={BarChart3}
          label="Today's Revenue"
          value={fmtEGP(todayRevenue)}
          delta="+12.4% vs yesterday"
          color="#6366F1"
        />
        <DemoKPI
          icon={ShoppingCart}
          label="Transactions"
          value={fmt(transactions)}
          delta="+8.1% vs last week"
          color="#22D3EE"
        />
        <DemoKPI
          icon={Users}
          label="Active Customers"
          value={fmt(customers)}
          delta="+5.3% vs last month"
          color="#34D399"
        />
        <DemoKPI
          icon={TrendingUp}
          label="Avg Basket Size"
          value={fmtEGP(avgBasket)}
          delta="+3.2% vs last month"
          color="#E5A00D"
        />
      </div>

      {/* Rolling trend chart */}
      <div
        className="rounded-xl p-5"
        style={{ background: "#161B22", border: "1px solid #21262D" }}
      >
        <div className="mb-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold" style={{ color: "#E6EDF3" }}>
              30-Day Revenue Trend
            </p>
            <p className="text-xs" style={{ color: "#8B949E" }}>
              Live-scrolling — a new data point arrives every 3 seconds
            </p>
          </div>
          <span
            className="flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold"
            style={{ background: "#34D39915", color: "#34D399" }}
          >
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400 inline-block" />
            LIVE
          </span>
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={trend} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="demoGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366F1" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#6366F1" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#21262D" vertical={false} />
            <XAxis
              dataKey="day"
              tick={{ fontSize: 10, fill: "#8B949E" }}
              axisLine={false}
              tickLine={false}
              interval={4}
            />
            <YAxis
              tickFormatter={(v: number) => fmt(v)}
              tick={{ fontSize: 10, fill: "#8B949E" }}
              axisLine={false}
              tickLine={false}
              width={52}
            />
            <Tooltip content={<ChartTooltip />} />
            <Area
              type="monotone"
              dataKey="revenue"
              stroke="#6366F1"
              strokeWidth={2}
              fill="url(#demoGradient)"
              dot={false}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Top products simulation */}
      <div
        className="rounded-xl p-5"
        style={{ background: "#161B22", border: "1px solid #21262D" }}
      >
        <p className="mb-4 text-sm font-semibold" style={{ color: "#E6EDF3" }}>
          Top Products by Revenue
        </p>
        <div className="space-y-2.5">
          {DEMO_PRODUCTS.map((p) => (
            <div key={p.name} className="flex items-center gap-3">
              <div
                className="w-28 truncate text-xs font-medium"
                style={{ color: "#E6EDF3" }}
              >
                {p.name}
              </div>
              <div className="flex-1 overflow-hidden rounded-full" style={{ background: "#21262D" }}>
                <div
                  className="h-2 rounded-full transition-all duration-500"
                  style={{ width: `${p.pct}%`, background: "#6366F1" }}
                />
              </div>
              <div className="w-16 text-right text-xs tabular-nums" style={{ color: "#8B949E" }}>
                {fmtEGP(p.rev)}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* CTA */}
      <div
        className="flex flex-col items-center gap-3 rounded-xl p-8 text-center"
        style={{ background: "#161B22", border: "1px solid #21262D" }}
      >
        <p className="text-base font-semibold" style={{ color: "#E6EDF3" }}>
          Ready to see your own data?
        </p>
        <p className="max-w-sm text-sm" style={{ color: "#8B949E" }}>
          Connect your Excel or CSV files and get a full analytics platform in minutes.
        </p>
        <a
          href="/login"
          className="inline-flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold transition-colors"
          style={{ background: "#6366F1", color: "#fff" }}
        >
          Get Started Free
          <ArrowUpRight className="h-4 w-4" />
        </a>
      </div>
    </div>
  );
}

// Static demo product data — kept outside the component to avoid re-creation
const DEMO_PRODUCTS: { name: string; rev: number; pct: number }[] = [
  { name: "Panadol Extra", rev: 42_800, pct: 92 },
  { name: "Brufen 400mg", rev: 38_500, pct: 83 },
  { name: "Vitamin C 1g", rev: 31_200, pct: 67 },
  { name: "Augmentin 1g", rev: 28_900, pct: 62 },
  { name: "Nexium 40mg", rev: 24_100, pct: 52 },
];
