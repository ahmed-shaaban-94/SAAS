"use client";

import { useEffect, useState } from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface SuccessAnimationProps {
  /** Whether to show the success checkmark */
  show: boolean;
  /** Duration in ms before returning to idle state (default: 1500) */
  duration?: number;
  /** Callback when animation completes */
  onComplete?: () => void;
  className?: string;
}

/**
 * Animated checkmark that appears briefly after a successful action.
 * Use `show` to trigger; it auto-resets after `duration` ms.
 */
export function SuccessAnimation({ show, duration = 1500, onComplete, className }: SuccessAnimationProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!show) return;
    setVisible(true);
    const timer = setTimeout(() => {
      setVisible(false);
      onComplete?.();
    }, duration);
    return () => clearTimeout(timer);
  }, [show, duration, onComplete]);

  if (!visible) return null;

  return (
    <span
      className={cn(
        "inline-flex items-center justify-center rounded-full bg-growth-green/10 text-growth-green",
        "animate-in zoom-in-50 fade-in duration-200",
        className,
      )}
      aria-live="polite"
      aria-label="Success"
    >
      <Check className="h-4 w-4" strokeWidth={2.5} />
    </span>
  );
}

/**
 * Hook-based wrapper: returns `{ trigger, isSuccess }`.
 * Call `trigger()` to flash the success state.
 */
export function useSuccessAnimation(duration = 1500) {
  const [isSuccess, setIsSuccess] = useState(false);

  const trigger = () => {
    setIsSuccess(true);
    setTimeout(() => setIsSuccess(false), duration);
  };

  return { isSuccess, trigger };
}
