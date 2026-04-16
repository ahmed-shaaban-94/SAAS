import { Check } from "lucide-react";
import Link from "next/link";
import type { PricingTier } from "@/lib/marketing-constants";

function getCtaHref(name: string): string {
  switch (name) {
    case "Explorer Pilot":
    case "Operations Pilot":
      return "#pilot-access";
    case "Enterprise Rollout":
      return "mailto:support@smartdatapulse.tech?subject=Enterprise%20Rollout";
    default:
      return "#pilot-access";
  }
}

export function PricingCard({
  name,
  price,
  originalPrice,
  period,
  description,
  badge,
  features,
  cta,
  isPopular,
}: PricingTier) {
  const href = getCtaHref(name);
  const isExternal = href.startsWith("mailto:");

  const cardContent = (
    <>
      {isPopular && (
        <span className="absolute -top-3 left-1/2 z-10 -translate-x-1/2 rounded-full bg-accent px-4 py-1 text-xs font-semibold text-page">
          Popular
        </span>
      )}

      <h3 className="text-lg font-semibold">{name}</h3>
      <p className="mt-1 text-sm text-text-secondary">{description}</p>

      <div className="mt-6">
        {originalPrice && (
          <span className="mr-2 text-xl text-text-secondary line-through">{originalPrice}</span>
        )}
        <span className="text-4xl font-bold">{price}</span>
        {period && <span className="text-text-secondary">{period}</span>}
      </div>
      {badge && (
        <div className="mt-3 inline-flex items-center gap-1.5 rounded-xl bg-growth-green/10 px-3 py-1.5 text-xs font-semibold text-growth-green">
          <span>🎉</span> {badge}
        </div>
      )}

      <ul className="mt-8 flex-1 space-y-3">
        {features.map((feature) => (
          <li key={feature} className="flex items-start gap-3">
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
            <span className="text-sm text-text-secondary">{feature}</span>
          </li>
        ))}
      </ul>

      {isExternal ? (
        <a
          href={href}
          className={`mt-8 block rounded-lg py-3 text-center text-sm font-semibold transition-colors ${
            isPopular
              ? "cta-shimmer bg-accent text-page shadow-lg shadow-accent/20 hover:bg-accent/90"
              : "viz-panel-soft text-text-primary hover:bg-white/10"
          }`}
        >
          {cta}
        </a>
      ) : (
        <Link
          href={href}
          className={`mt-8 block rounded-lg py-3 text-center text-sm font-semibold transition-colors ${
            isPopular
              ? "cta-shimmer bg-accent text-page shadow-lg shadow-accent/20 hover:bg-accent/90"
              : "viz-panel-soft text-text-primary hover:bg-white/10"
          }`}
        >
          {cta}
        </Link>
      )}
    </>
  );

  if (isPopular) {
    return (
      <div className="rotating-border">
        <div className="relative flex flex-col rounded-[1.75rem] p-8 bg-accent/5">
          {cardContent}
        </div>
      </div>
    );
  }

  return (
    <div className="viz-panel viz-card-hover relative flex flex-col rounded-[1.75rem] p-8 hover-lift">
      {cardContent}
    </div>
  );
}
