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
}

const DARK_CHART_THEME: ChartTheme = {
  tickFill: "#A8B3BD",
  tickFontSize: 11,
  gridStroke: "#21262D",
  axisStroke: "#30363D",
  tooltipBg: "#161B22",
  tooltipBorder: "#30363D",
  tooltipColor: "#E6EDF3",
  accentColor: "#FF5722",
  chartBlue: "#26A69A",
  chartAmber: "#FFB300",
  cardBg: "#161B22",
};

const LIGHT_CHART_THEME: ChartTheme = {
  tickFill: "#57606A",
  tickFontSize: 11,
  gridStroke: "#D0D7DE",
  axisStroke: "#D0D7DE",
  tooltipBg: "#FFFFFF",
  tooltipBorder: "#D0D7DE",
  tooltipColor: "#1F2328",
  accentColor: "#FF4500",
  chartBlue: "#FF4500",
  chartAmber: "#F9A825",
  cardBg: "#FFFFFF",
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
