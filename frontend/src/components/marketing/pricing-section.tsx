"use client";

import { SectionWrapper } from "./section-wrapper";
import { PricingCard } from "./pricing-card";
import { PRICING_TIERS } from "@/lib/marketing-constants";
import { useIntersectionObserver } from "@/hooks/use-intersection-observer";

export function PricingSection() {
  const { ref, isVisible } = useIntersectionObserver();

  return (
    <SectionWrapper id="pricing">
      <div ref={ref} className={`animate-on-scroll ${isVisible ? "is-visible" : ""}`}>
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-bold sm:text-4xl">
            Simple, transparent{" "}
            <span className="gradient-text">pricing</span>
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-text-secondary">
            Start free, scale when you need to. No hidden fees, no surprises.
          </p>
        </div>

        <div className="grid gap-8 lg:grid-cols-3">
          {PRICING_TIERS.map((tier) => (
            <PricingCard key={tier.name} {...tier} />
          ))}
        </div>
      </div>
    </SectionWrapper>
  );
}
