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
  "#20BCE5", // cyan
  "#1DD48B", // emerald
  "#FFAB3D", // amber
  "#7467F8", // violet
  "#FF7B7B", // coral
  "#70E1FF", // sky
  "#FFD166", // gold
  "#627D98", // slate
] as const;

const LIGHT_PALETTE = [
  "#1CB9E7", // cyan
  "#1CC985", // emerald
  "#FFAB3D", // amber
  "#6F61F6", // violet
  "#F46D75", // coral
  "#18A4D0", // sky
  "#FFC94A", // gold
  "#31567D", // slate
] as const;

const DARK_CHART_THEME: ChartTheme = {
  tickFill: "#B8C0CC",
  tickFontSize: 11,
  gridStroke: "#33506B",
  axisStroke: "#46627C",
  tooltipBg: "#102A43",
  tooltipBorder: "#33506B",
  tooltipColor: "#F7FBFF",
  accentColor: "#00C7F2",
  chartBlue: "#20BCE5",
  chartAmber: "#FFAB3D",
  cardBg: "#102A43",
  palette: DARK_PALETTE,
};

const LIGHT_CHART_THEME: ChartTheme = {
  tickFill: "#627D98",
  tickFontSize: 11,
  gridStroke: "#D7E2EC",
  axisStroke: "#D7E2EC",
  tooltipBg: "#FFFFFF",
  tooltipBorder: "#D7E2EC",
  tooltipColor: "#102A43",
  accentColor: "#00C7F2",
  chartBlue: "#1CB9E7",
  chartAmber: "#FFAB3D",
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
