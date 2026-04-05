"use client";

import { useRef, useEffect, useState } from "react";
import { SectionWrapper } from "./section-wrapper";
import { FeatureCard } from "./feature-card";
import { FEATURES } from "@/lib/marketing-constants";

export function FeaturesGrid() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.unobserve(el);
        }
      },
      { threshold: 0.1 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <SectionWrapper id="features">
      <div ref={containerRef}>
        <div className={`mb-12 text-center reveal-up ${isVisible ? "is-visible" : ""}`}>
          <h2 className="text-3xl font-bold sm:text-4xl">
            Everything you need to{" "}
            <span className="gradient-text-animated">master your data</span>
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-text-secondary">
            From raw Excel files to AI-powered insights, Data Pulse handles every
            step of your sales analytics pipeline.
          </p>
        </div>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature, i) => (
            <div
              key={feature.title}
              className={`stagger-card ${isVisible ? "revealed" : ""} ${
                i === 0 || i === 4 ? "sm:col-span-2" : ""
              }`}
              style={{ transitionDelay: `${i * 100}ms` }}
            >
              <FeatureCard {...feature} isBento={i === 0 || i === 4} />
            </div>
          ))}
        </div>
      </div>
    </SectionWrapper>
  );
}
