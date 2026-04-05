"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface NumberPulseProps {
  children: React.ReactNode;
  value?: number;
  className?: string;
}

/**
 * Wraps a number display — briefly flashes green/red when value changes.
 */
export function NumberPulse({ children, value, className }: NumberPulseProps) {
  const prevValue = useRef(value);
  const [pulse, setPulse] = useState<"up" | "down" | null>(null);

  useEffect(() => {
    if (prevValue.current === undefined || value === undefined) {
      prevValue.current = value;
      return;
    }
    if (value > prevValue.current) {
      setPulse("up");
    } else if (value < prevValue.current) {
      setPulse("down");
    }
    prevValue.current = value;

    const timer = setTimeout(() => setPulse(null), 600);
    return () => clearTimeout(timer);
  }, [value]);

  return (
    <span
      className={cn(
        "inline-block transition-all duration-300",
        pulse === "up" && "number-pulse-green",
        pulse === "down" && "number-pulse-red",
        className,
      )}
    >
      {children}
    </span>
  );
}
