import { SectionWrapper } from "./section-wrapper";
import { TECH_BADGES } from "@/lib/marketing-constants";

export function TechBadges() {
  return (
    <SectionWrapper>
      <div className="text-center">
        <p className="mb-6 text-sm font-medium text-text-secondary">
          Built with industry-leading technologies
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          {TECH_BADGES.map((badge) => (
            <span
              key={badge}
              className="rounded-full border border-border bg-card px-4 py-2 text-sm font-medium text-text-secondary transition-colors hover:border-accent/30 hover:text-accent"
            >
              {badge}
            </span>
          ))}
        </div>
      </div>
    </SectionWrapper>
  );
}
