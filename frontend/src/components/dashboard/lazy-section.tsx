"use client";

import type { ReactNode } from "react";
import { useInView } from "@/hooks/use-in-view";
import { cn } from "@/lib/utils";

interface LazySectionProps {
  children: ReactNode;
  minHeight?: string;
  className?: string;
  stagger?: boolean;
}

export function LazySection({ children, minHeight = "200px", className, stagger = false }: LazySectionProps) {
  const { ref, inView } = useInView({ rootMargin: "0px" });

  return (
    <div
      ref={ref}
      className={cn(
        className,
        stagger && "stagger-container",
        stagger && inView && "stagger-visible",
      )}
      style={inView ? undefined : { minHeight }}
    >
      {inView ? children : null}
    </div>
  );
}
