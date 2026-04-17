"use client";

import { SectionWrapper } from "./section-wrapper";
import { useIntersectionObserver } from "@/hooks/use-intersection-observer";

export function CTASection() {
  const { ref, isVisible } = useIntersectionObserver();

  return (
    <SectionWrapper>
      <div
        ref={ref}
        className={`reveal-up ${isVisible ? "is-visible" : ""}`}
      >
        <div className="viz-panel relative overflow-hidden rounded-[2rem] p-8 text-center sm:p-12">
          {/* Background glow */}
          <div className="pointer-events-none absolute inset-0">
            <div className="absolute left-1/2 top-1/2 h-[300px] w-[300px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent/10 blur-[80px]" />
          </div>

          <div className="relative">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.26em] text-accent/80">
              Start with clarity
            </p>
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl">
              See what your team should act on every day.
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-lg leading-8 text-text-secondary">
              If your sales and operations data lives across spreadsheets, manual reports,
              and disconnected workflows, DataPulse can help you turn it into one clearer
              operating view.
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
              {/* PHASE 4: Replace with <LeadCaptureModal trigger="Request Pilot Access" /> */}
              <a
                href="#pilot-access"
                className="rounded-full bg-accent px-8 py-3.5 text-sm font-semibold text-page shadow-[0_0_24px_rgba(0,199,242,0.35)] transition-all hover:shadow-[0_0_32px_rgba(0,199,242,0.5)] hover:scale-[1.02]"
              >
                Request Pilot Access
              </a>
              <a
                href="/demo"
                className="rounded-full border border-white/15 bg-white/5 px-8 py-3.5 text-sm font-semibold text-text-primary transition-colors hover:bg-white/10"
              >
                See Product Demo
              </a>
            </div>
            <p className="mt-4 text-sm text-text-secondary/70">
              Best for teams that want to prove value in a focused rollout before
              expanding company-wide.
            </p>
          </div>
        </div>
      </div>
    </SectionWrapper>
  );
}
