"use client";

import { ChevronDown } from "lucide-react";
import type { FAQItem } from "@/lib/marketing-constants";

interface FAQItemProps extends FAQItem {
  isOpen: boolean;
  onToggle: () => void;
}

export function FAQItemCard({ question, answer, isOpen, onToggle }: FAQItemProps) {
  return (
    <div className="border-b border-border">
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between py-5 text-left"
        aria-expanded={isOpen}
      >
        <span className="pr-4 text-sm font-medium sm:text-base">{question}</span>
        <ChevronDown
          className={`h-5 w-5 shrink-0 text-text-secondary transition-transform duration-200 ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>
      <div
        className={`grid transition-all duration-200 ${
          isOpen ? "grid-rows-[1fr] pb-5" : "grid-rows-[0fr]"
        }`}
      >
        <div className="overflow-hidden">
          <p className="text-sm leading-relaxed text-text-secondary">{answer}</p>
        </div>
      </div>
    </div>
  );
}
