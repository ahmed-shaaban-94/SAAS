"use client";

import { SectionWrapper } from "./section-wrapper";
import { FeatureCard } from "./feature-card";
import { FEATURES } from "@/lib/marketing-constants";
import { useIntersectionObserver } from "@/hooks/use-intersection-observer";

export function FeaturesGrid() {
  const { ref, isVisible } = useIntersectionObserver();

  return (
    <SectionWrapper id="features">
      <div ref={ref} className={`animate-on-scroll ${isVisible ? "is-visible" : ""}`}>
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-bold sm:text-4xl">
            Everything you need to{" "}
            <span className="gradient-text">master your data</span>
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-text-secondary">
            From raw Excel files to AI-powered insights, DataPulse handles every
            step of your sales analytics pipeline.
          </p>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature) => (
            <FeatureCard key={feature.title} {...feature} />
          ))}
        </div>
      </div>
    </SectionWrapper>
  );
}
