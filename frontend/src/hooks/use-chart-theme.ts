"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

export interface ChartTheme {
  tickFill: string;
  tickFontSize: number;
  gridStroke: string;
  axisStroke: string;
  tooltipBg: string;
  tooltipBorder: string;
  tooltipColor: string;
  accentColor: string;
  chartBlue: string;
  chartAmber: string;
  cardBg: string;
  /** 8-color palette for multi-series charts */
  palette: readonly string[];
}

const DARK_PALETTE = [
  "#6366F1", // indigo
  "#E5A00D", // amber
  "#A78BFA", // violet
  "#22D3EE", // cyan
  "#34D399", // emerald
  "#818CF8", // indigo-light
  "#FB923C", // orange
  "#60A5FA", // blue-light
] as const;

const LIGHT_PALETTE = [
  "#4F46E5", // indigo
  "#D97706", // amber
  "#8B5CF6", // violet
  "#0891B2", // cyan
  "#059669", // emerald
  "#6366F1", // indigo-light
  "#EA580C", // orange
  "#2563EB", // blue
] as const;

const DARK_CHART_THEME: ChartTheme = {
  tickFill: "#A8B3BD",
  tickFontSize: 11,
  gridStroke: "#21262D",
  axisStroke: "#30363D",
  tooltipBg: "#161B22",
  tooltipBorder: "#30363D",
  tooltipColor: "#E6EDF3",
  accentColor: "#E5A00D",
  chartBlue: "#6366F1",
  chartAmber: "#E5A00D",
  cardBg: "#161B22",
  palette: DARK_PALETTE,
};

const LIGHT_CHART_THEME: ChartTheme = {
  tickFill: "#57606A",
  tickFontSize: 11,
  gridStroke: "#D0D7DE",
  axisStroke: "#D0D7DE",
  tooltipBg: "#FFFFFF",
  tooltipBorder: "#D0D7DE",
  tooltipColor: "#1F2328",
  accentColor: "#D97706",
  chartBlue: "#4F46E5",
  chartAmber: "#D97706",
  cardBg: "#FFFFFF",
  palette: LIGHT_PALETTE,
};

export function useChartTheme(): ChartTheme {
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted || resolvedTheme === "dark") {
    return DARK_CHART_THEME;
  }
  return LIGHT_CHART_THEME;
}
