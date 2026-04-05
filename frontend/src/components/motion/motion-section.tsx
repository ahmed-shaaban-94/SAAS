"use client";

import { motion, useInView } from "framer-motion";
import { useRef } from "react";
import { cn } from "@/lib/utils";

interface MotionSectionProps {
  children: React.ReactNode;
  className?: string;
  /** Only animate once when entering viewport */
  once?: boolean;
}

/**
 * Section that fades in when scrolled into view.
 * Replaces CSS .animate-on-scroll with framer-motion's useInView.
 */
export function MotionSection({ children, className, once = true }: MotionSectionProps) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once, margin: "-50px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 30 }}
      animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className={cn(className)}
    >
      {children}
    </motion.div>
  );
}
