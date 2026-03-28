"use client";

import { useEffect, useState } from "react";
import { SectionWrapper } from "./section-wrapper";
import { STATS } from "@/lib/marketing-constants";
import { useIntersectionObserver } from "@/hooks/use-intersection-observer";

function AnimatedStat({
  value,
  label,
  isVisible,
}: {
  value: string;
  label: string;
  isVisible: boolean;
}) {
  return (
    <div className="text-center">
      <p
        className={`text-3xl font-bold text-accent sm:text-4xl ${
          isVisible ? "animate-count-up" : "opacity-0"
        }`}
      >
        {value}
      </p>
      <p className="mt-1 text-sm text-text-secondary">{label}</p>
    </div>
  );
}

export function StatsBanner() {
  const { ref, isVisible } = useIntersectionObserver({ threshold: 0.3 });

  return (
    <SectionWrapper variant="gradient">
      <div
        ref={ref}
        className="rounded-2xl border border-border bg-card/80 px-6 py-12 backdrop-blur"
      >
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
          {STATS.map((stat) => (
            <AnimatedStat
              key={stat.label}
              value={stat.value}
              label={stat.label}
              isVisible={isVisible}
            />
          ))}
        </div>
      </div>
    </SectionWrapper>
  );
}
