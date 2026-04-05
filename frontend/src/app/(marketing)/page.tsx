import { HeroSection } from "@/components/marketing/hero-section";
import { TrustBar } from "@/components/marketing/trust-bar";
import { FeaturesGrid } from "@/components/marketing/features-grid";
import { HowItWorks } from "@/components/marketing/how-it-works";
import { StatsBanner } from "@/components/marketing/stats-banner";
import { PricingSection } from "@/components/marketing/pricing-section";
import { FAQSection } from "@/components/marketing/faq-section";
import { TechBadges } from "@/components/marketing/tech-badges";
import { CTASection } from "@/components/marketing/cta-section";
import { JsonLd } from "@/components/marketing/json-ld";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "DataPulse - Turn Raw Sales Data into Revenue Intelligence",
  description:
    "Import, clean, analyze, and visualize your sales data with an automated medallion pipeline. AI-powered insights, real-time dashboards, and enterprise-grade quality gates.",
  alternates: {
    canonical: "/",
  },
};

export default function LandingPage() {
  return (
    <>
      <JsonLd />
      <HeroSection />
      <TrustBar />
      <FeaturesGrid />
      <HowItWorks />
      <StatsBanner />
      <PricingSection />
      <FAQSection />
      <TechBadges />
      <CTASection />
    </>
  );
}
