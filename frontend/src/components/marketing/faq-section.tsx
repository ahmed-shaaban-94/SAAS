"use client";

import { useState } from "react";
import { SectionWrapper } from "./section-wrapper";
import { FAQItemCard } from "./faq-item";
import { FAQ_ITEMS } from "@/lib/marketing-constants";
import { useIntersectionObserver } from "@/hooks/use-intersection-observer";

export function FAQSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const { ref, isVisible } = useIntersectionObserver();

  return (
    <SectionWrapper id="faq" variant="alternate">
      <div ref={ref} className={`animate-on-scroll ${isVisible ? "is-visible" : ""}`}>
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-bold sm:text-4xl">
            Frequently asked{" "}
            <span className="gradient-text">questions</span>
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-text-secondary">
            Everything you need to know about DataPulse.
          </p>
        </div>

        <div className="mx-auto max-w-3xl">
          {FAQ_ITEMS.map((item, i) => (
            <FAQItemCard
              key={item.question}
              {...item}
              isOpen={openIndex === i}
              onToggle={() => setOpenIndex(openIndex === i ? null : i)}
            />
          ))}
        </div>
      </div>
    </SectionWrapper>
  );
}
