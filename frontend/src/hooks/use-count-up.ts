"use client";

import { useEffect, useRef, useState } from "react";

interface UseCountUpOptions {
  end: number;
  duration?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  separator?: string;
}

function easeOutExpo(t: number): number {
  return t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
}

function formatWithSeparator(num: number, decimals: number, separator: string): string {
  const fixed = num.toFixed(decimals);
  const [intPart, decPart] = fixed.split(".");
  const formatted = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, separator);
  return decPart ? `${formatted}.${decPart}` : formatted;
}

export function useCountUp({
  end,
  duration = 1200,
  decimals = 0,
  prefix = "",
  suffix = "",
  separator = ",",
}: UseCountUpOptions): string {
  const [display, setDisplay] = useState(`${prefix}${formatWithSeparator(0, decimals, separator)}${suffix}`);
  const rafRef = useRef<number>(0);
  const prevEnd = useRef(end);

  useEffect(() => {
    const startVal = prevEnd.current !== end ? prevEnd.current : 0;
    prevEnd.current = end;

    const startTime = performance.now();

    function tick(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = easeOutExpo(progress);
      const current = startVal + (end - startVal) * eased;

      setDisplay(`${prefix}${formatWithSeparator(current, decimals, separator)}${suffix}`);

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(tick);
      }
    }

    rafRef.current = requestAnimationFrame(tick);

    return () => cancelAnimationFrame(rafRef.current);
  }, [end, duration, decimals, prefix, suffix, separator]);

  return display;
}
