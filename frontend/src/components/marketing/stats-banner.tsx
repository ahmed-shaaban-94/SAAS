"use client";

import { SectionWrapper } from "./section-wrapper";
import { CLAIMS } from "@/lib/marketing-constants";
import { useIntersectionObserver } from "@/hooks/use-intersection-observer";
import {
  Clock,
  Eye,
  AlertTriangle,
  Zap,
  type LucideIcon,
} from "lucide-react";

const ICON_MAP: Record<string, LucideIcon> = {
  Clock,
  Eye,
  AlertTriangle,
  Zap,
};

export function StatsBanner() {
  const { ref, isVisible } = useIntersectionObserver();

  return (
    <SectionWrapper variant="gradient">
      <div
        ref={ref}
        className={`viz-panel rounded-[2rem] px-6 py-12 backdrop-blur transition-opacity duration-700 ${
          isVisible ? "opacity-100" : "opacity-0"
        }`}
      >
        <div className="absolute inset-x-8 top-0 h-1 rounded-b-full bg-gradient-to-r from-chart-blue via-accent to-chart-purple" />
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {CLAIMS.map((claim) => {
            const Icon = ICON_MAP[claim.icon];
            return (
              <div key={claim.headline} className="flex flex-col gap-2">
                {Icon && <Icon className="h-5 w-5 text-accent" />}
                <p className="text-base font-semibold text-text-primary leading-snug">
                  {claim.headline}
                </p>
                <p className="text-sm text-text-secondary leading-relaxed">
                  {claim.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </SectionWrapper>
  );
}
