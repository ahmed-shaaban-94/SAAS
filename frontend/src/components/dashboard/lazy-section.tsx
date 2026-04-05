"use client";

import type { ReactNode } from "react";
import { useInView } from "@/hooks/use-in-view";

interface LazySectionProps {
  children: ReactNode;
  minHeight?: string;
  className?: string;
}

export function LazySection({ children, minHeight = "200px", className }: LazySectionProps) {
  const { ref, inView } = useInView();

  return (
    <div ref={ref} className={className} style={inView ? undefined : { minHeight }}>
      {inView ? children : null}
    </div>
  );
}
