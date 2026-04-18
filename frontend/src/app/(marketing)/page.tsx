import type { Metadata } from "next";
import { EditorialLanding } from "@/components/marketing/editorial-landing";
import { JsonLd } from "@/components/marketing/json-ld";

export const metadata: Metadata = {
  title: "DataPulse — the heartbeat of your business",
  description:
    "DataPulse reads 1.1M transactions across your pharmacy branches every day and wakes you up each morning with a single paragraph of what matters. Every number is explainable. Every trend has a cause.",
  alternates: {
    canonical: "/",
  },
};

export default function LandingPage() {
  return (
    <>
      <JsonLd />
      <EditorialLanding />
    </>
  );
}
