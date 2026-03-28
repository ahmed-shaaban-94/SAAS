"use client";

import { SectionWrapper } from "./section-wrapper";
import { PipelineStepCard } from "./pipeline-step";
import { PIPELINE_STEPS } from "@/lib/marketing-constants";
import { useIntersectionObserver } from "@/hooks/use-intersection-observer";

export function HowItWorks() {
  const { ref, isVisible } = useIntersectionObserver();

  return (
    <SectionWrapper id="how-it-works" variant="alternate">
      <div ref={ref} className={`animate-on-scroll ${isVisible ? "is-visible" : ""}`}>
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-bold sm:text-4xl">
            How <span className="gradient-text">DataPulse</span> works
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-text-secondary">
            Your data flows through four stages, each adding more value. From
            raw import to intelligent dashboards.
          </p>
        </div>

        {/* Desktop: horizontal, Mobile: vertical */}
        <div className="flex flex-col gap-8 md:flex-row md:gap-4">
          {PIPELINE_STEPS.map((step, i) => (
            <PipelineStepCard
              key={step.label}
              {...step}
              isLast={i === PIPELINE_STEPS.length - 1}
            />
          ))}
        </div>
      </div>
    </SectionWrapper>
  );
}
