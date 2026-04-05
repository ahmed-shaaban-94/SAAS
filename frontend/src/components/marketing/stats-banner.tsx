"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { SectionWrapper } from "./section-wrapper";
import { STATS } from "@/lib/marketing-constants";

function useCountUp(target: number, isActive: boolean, duration = 2000) {
  const [value, setValue] = useState(0);
  const hasRun = useRef(false);

  useEffect(() => {
    if (!isActive || hasRun.current) return;
    hasRun.current = true;

    const start = performance.now();
    function step(now: number) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      setValue(eased * target);
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }, [isActive, target, duration]);

  return value;
}

function AnimatedStat({
  numericValue,
  suffix,
  label,
  isVisible,
}: {
  numericValue: number;
  suffix: string;
  label: string;
  isVisible: boolean;
}) {
  const current = useCountUp(numericValue, isVisible);

  const formatValue = useCallback(
    (v: number) => {
      if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
      if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
      if (suffix === "%" || suffix === "x") return v.toFixed(1);
      return Math.floor(v).toString();
    },
    [suffix]
  );

  return (
    <div className="text-center">
      <p
        className={`text-3xl font-bold text-accent sm:text-4xl tabular-nums transition-opacity duration-500 ${
          isVisible ? "opacity-100" : "opacity-0"
        }`}
      >
        {formatValue(current)}
        {suffix}
      </p>
      <p className="mt-1 text-sm text-text-secondary">{label}</p>
    </div>
  );
}

export function StatsBanner() {
  const ref = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.unobserve(el);
        }
      },
      { threshold: 0.3 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

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
              numericValue={stat.numericValue}
              suffix={stat.suffix}
              label={stat.label}
              isVisible={isVisible}
            />
          ))}
        </div>
      </div>
    </SectionWrapper>
  );
}
