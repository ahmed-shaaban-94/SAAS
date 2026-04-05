"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface MotionCardProps {
  children: React.ReactNode;
  className?: string;
  index?: number;
  /** Delay per item for stagger effect (default 0.08s) */
  staggerDelay?: number;
}

/**
 * Animated card wrapper — fade-in + slide-up with stagger based on index.
 * Respects prefers-reduced-motion via framer-motion's built-in support.
 */
export function MotionCard({ children, className, index = 0, staggerDelay = 0.08 }: MotionCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.4,
        delay: index * staggerDelay,
        ease: [0.25, 0.46, 0.45, 0.94],
      }}
      className={cn(className)}
    >
      {children}
    </motion.div>
  );
}
