"use client";

import { useEffect, useState } from "react";
import { Settings } from "lucide-react";
import { useTranslations } from "next-intl";
import { BrandDot } from "./BrandDot";
import { ConnectionPill } from "./ConnectionPill";
import { TabSwitcher, type PosScreen } from "./TabSwitcher";

export interface TopBarProps {
  screen: PosScreen;
  online: boolean;
  queueDepth?: number;
  cashierName: string;
  onSwitchScreen: (screen: PosScreen) => void;
  /** Optional per-tab badge counts (e.g. `{ sync: 5 }`). */
  tabBadges?: Partial<Record<PosScreen, number>>;
  /** Optional handler for the settings cog. */
  onOpenSettings?: () => void;
}

/**
 * TopBar — POS shell header.
 *
 * Matches `docs/design/pos-terminal/frames/pos/shell.jsx`:
 *   [brand dot] DataPulse · POS    |    [tabs]    |    [connection pill]  [cashier]  [clock]  [settings]
 *
 * Uses logical properties where possible so the shell flips cleanly in RTL.
 */
export function TopBar({
  screen,
  online,
  queueDepth = 0,
  cashierName,
  onSwitchScreen,
  tabBadges,
  onOpenSettings,
}: TopBarProps) {
  const t = useTranslations("app.pos");
  const [clock, setClock] = useState<string>(() => formatClock(new Date()));

  useEffect(() => {
    const id = setInterval(() => setClock(formatClock(new Date())), 20_000);
    return () => clearInterval(id);
  }, []);

  return (
    <header
      className="pos-root relative z-10 w-full"
      style={{
        borderBottom: "1px solid var(--pos-line, rgba(255,255,255,0.06))",
        background:
          "linear-gradient(180deg, rgba(5, 14, 23, 0.95), rgba(8, 24, 38, 0.9))",
        backdropFilter: "blur(16px)",
      }}
      data-testid="pos-topbar"
    >
      {/* Row 1 — brand + status + cashier/clock */}
      <div
        className="flex items-center gap-4"
        style={{
          paddingInline: "20px",
          paddingBlock: "10px",
        }}
      >
        {/* Brand cluster */}
        <div className="flex items-center gap-3 min-w-0">
          <BrandDot />
          <div
            className="pos-display truncate text-[17px] font-medium"
            style={{ letterSpacing: "-0.01em" }}
          >
            DataPulse
            <span
              className="font-normal"
              style={{ color: "var(--pos-ink-3, #7a8494)" }}
            >
              {" · "}
              {t("brandSuffix")}
            </span>
          </div>
        </div>

        {/* Pulse separator — flexible spacer keeps layout responsive. */}
        <div
          className="hidden h-5 w-px md:block"
          style={{ background: "var(--pos-line-strong, rgba(255,255,255,0.12))" }}
          aria-hidden="true"
        />
        <PulseLine online={online} />

        {/* Right cluster */}
        <div
          className="ms-auto flex items-center gap-3"
          style={{ marginInlineStart: "auto" }}
        >
          <ConnectionPill online={online} queueDepth={queueDepth} />

          <div
            className="hidden flex-col items-end sm:flex"
            style={{ textAlign: "end" }}
          >
            <span
              className="pos-mono uppercase"
              style={{
                fontSize: 9.5,
                letterSpacing: "0.18em",
                color: "var(--pos-ink-4, #3f4a5a)",
              }}
            >
              {t("cashier")}
            </span>
            <span
              className="text-[13px] font-semibold"
              style={{ color: "var(--pos-ink-1, #e8ecf2)" }}
            >
              {cashierName}
            </span>
          </div>

          <div
            className="pos-mono tabular-nums text-[12px] font-semibold"
            style={{
              color: "var(--pos-ink-2, #b8c0cc)",
              padding: "6px 9px",
              border: "1px solid var(--pos-line, rgba(255,255,255,0.06))",
              borderRadius: "var(--pos-radius-pill, 6px)",
            }}
            aria-label="Current time"
          >
            {clock}
          </div>

          {onOpenSettings ? (
            <button
              type="button"
              onClick={onOpenSettings}
              aria-label={t("settings")}
              className="inline-flex h-8 w-8 items-center justify-center rounded-[var(--pos-radius-btn,8px)]"
              style={{
                color: "var(--pos-ink-3, #7a8494)",
                border: "1px solid var(--pos-line, rgba(255,255,255,0.06))",
                background: "transparent",
              }}
            >
              <Settings size={16} aria-hidden="true" />
            </button>
          ) : null}
        </div>
      </div>

      {/* Row 2 — tab switcher */}
      <div
        className="flex items-center"
        style={{ paddingInline: "20px", paddingBlockEnd: "10px" }}
      >
        <TabSwitcher
          screen={screen}
          onSwitchScreen={onSwitchScreen}
          badges={tabBadges}
        />
      </div>
    </header>
  );
}

function formatClock(d: Date): string {
  return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

/**
 * Lightweight animated pulse line matching shell.jsx MiniPulseLine.
 * Rendered as a sine-wave SVG; offline = flat amber.
 */
function PulseLine({ online }: { online: boolean }) {
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!online) return;
    const id = setInterval(() => setTick((x) => x + 1), 1200);
    return () => clearInterval(id);
  }, [online]);

  const n = 60;
  const points: [number, number][] = [];
  for (let i = 0; i < n; i++) {
    const x = (i / (n - 1)) * 100;
    if (!online) {
      points.push([x, 50]);
      continue;
    }
    const seed =
      Math.sin((i + tick * 3) * 1.3) * Math.cos((i - tick * 2) * 0.7);
    const spike = i === n - 5 ? 1.6 : i === n - 4 ? -0.8 : 0;
    const y = 50 + seed * 10 + spike * 8;
    points.push([x, y]);
  }

  const path =
    "M " +
    points.map((p) => `${p[0].toFixed(2)},${p[1].toFixed(2)}`).join(" L ");

  return (
    <div
      className="hidden min-w-[120px] max-w-[320px] flex-1 md:block"
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        style={{ width: "100%", height: 26, display: "block" }}
      >
        <defs>
          <linearGradient id="pos-pulse-grad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#00c7f2" stopOpacity="0.2" />
            <stop offset="50%" stopColor="#00c7f2" stopOpacity="1" />
            <stop offset="100%" stopColor="#5cdfff" stopOpacity="1" />
          </linearGradient>
        </defs>
        <path
          d={path}
          fill="none"
          stroke={online ? "url(#pos-pulse-grad)" : "rgba(255,171,61,0.6)"}
          strokeWidth="1.2"
          vectorEffect="non-scaling-stroke"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {online ? (
          <circle
            cx={points[points.length - 1][0]}
            cy={points[points.length - 1][1]}
            r="1.6"
            fill="#5cdfff"
          />
        ) : null}
      </svg>
    </div>
  );
}
