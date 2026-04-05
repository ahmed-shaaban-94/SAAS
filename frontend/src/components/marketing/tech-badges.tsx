"use client";

import { SectionWrapper } from "./section-wrapper";
import { TECH_BADGES } from "@/lib/marketing-constants";
import { useIntersectionObserver } from "@/hooks/use-intersection-observer";

export function TechBadges() {
  const { ref, isVisible } = useIntersectionObserver();

  return (
    <SectionWrapper>
      <div ref={ref} className={`text-center reveal-up ${isVisible ? "is-visible" : ""}`}>
        <p className="mb-6 text-sm font-medium text-text-secondary">
          Built with industry-leading technologies
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          {TECH_BADGES.map((badge, i) => (
            <span
              key={badge}
              className={`rounded-full border border-border bg-card px-4 py-2 text-sm font-medium text-text-secondary transition-all hover:border-accent/30 hover:text-accent hover:shadow-[0_0_15px_rgba(255,69,0,0.1)] stagger-card ${
                isVisible ? "revealed" : ""
              }`}
              style={{ transitionDelay: `${i * 60}ms` }}
            >
              {badge}
            </span>
          ))}
        </div>
      </div>
    </SectionWrapper>
  );
}
