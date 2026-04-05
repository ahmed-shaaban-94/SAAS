"use client";

import { SectionWrapper } from "./section-wrapper";
import { WaitlistForm } from "./waitlist-form";
import { useIntersectionObserver } from "@/hooks/use-intersection-observer";

export function CTASection() {
  const { ref, isVisible } = useIntersectionObserver();

  return (
    <SectionWrapper>
      <div
        ref={ref}
        className={`reveal-up ${isVisible ? "is-visible" : ""}`}
      >
        <div className="relative rounded-2xl border border-accent/20 bg-gradient-to-br from-accent/5 via-card to-chart-blue/5 p-8 text-center sm:p-12 overflow-hidden">
          {/* Background glow */}
          <div className="pointer-events-none absolute inset-0">
            <div className="absolute left-1/2 top-1/2 h-[300px] w-[300px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent/10 blur-[80px]" />
          </div>

          <div className="relative">
            <h2 className="text-3xl font-bold sm:text-4xl">
              Ready to transform your sales data?
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-text-secondary">
              Join the waitlist and be the first to know when Data Pulse launches.
              Start turning raw data into revenue intelligence.
            </p>
            <div className="mt-8 flex justify-center">
              <WaitlistForm />
            </div>
          </div>
        </div>
      </div>
    </SectionWrapper>
  );
}
