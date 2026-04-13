"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

interface LoadingCardProps {
  className?: string;
  lines?: number;
  layoutId?: string;
}

export function LoadingCard({ className, lines = 3, layoutId }: LoadingCardProps) {
  const prefersReducedMotion = useReducedMotion();

  const inner = (
    <>
      {/* Subtle top accent shimmer */}
      <div className="absolute inset-x-0 top-0 h-1 shimmer-accent" />

      <div className="shimmer-line mb-4 h-4 w-1/3 rounded-md" />
      <div className="shimmer-line mb-3 h-7 w-2/3 rounded-md" />
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="shimmer-line mb-2.5 h-3 rounded-md"
          style={{ width: `${90 - i * 12}%` }}
        />
      ))}

      {/* Pulse glow overlay */}
      <div className="absolute inset-0 rounded-[var(--radius-card)] loading-pulse-glow" />
    </>
  );

  const baseClassName = cn(
    "relative overflow-hidden rounded-[var(--radius-card)] border border-border bg-card/80 backdrop-blur-sm p-6",
    "animate-fade-in",
    className,
  );

  // No layoutId or reduced motion: render plain div (no framer overhead)
  if (!layoutId || prefersReducedMotion) {
    return (
      <div className={baseClassName}>
        {inner}
      </div>
    );
  }

  return (
    <motion.div
      layoutId={layoutId}
      layout
      exit={{ opacity: 0, scale: 0.98 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={baseClassName}
    >
      {inner}
    </motion.div>
  );
}

// Alias for semantic clarity
export const SkeletonCard = LoadingCard;

// ─── AnimatedCard ──────────────────────────────────────────────────────────────
// Wrap real content with this to claim the same layoutId as the skeleton,
// creating a smooth morph transition when the skeleton is replaced.

interface AnimatedCardProps {
  layoutId?: string;
  className?: string;
  children: React.ReactNode;
}

export function AnimatedCard({ layoutId, className, children }: AnimatedCardProps) {
  const prefersReducedMotion = useReducedMotion();

  if (!layoutId || prefersReducedMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      layoutId={layoutId}
      layout
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// ─── CardPresence ──────────────────────────────────────────────────────────────
// Convenience re-export of AnimatePresence. Use this to wrap the conditional
// render of SkeletonCard / AnimatedCard so exit animations fire correctly.
//
// Usage:
//   <CardPresence>
//     {isLoading
//       ? <SkeletonCard layoutId="my-card" />
//       : <AnimatedCard layoutId="my-card">...</AnimatedCard>
//     }
//   </CardPresence>

export { AnimatePresence as CardPresence };
