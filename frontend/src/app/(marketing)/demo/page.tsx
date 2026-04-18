import type { Metadata } from "next";
import Link from "next/link";
import { SectionWrapper } from "@/components/marketing/section-wrapper";
import { LeadCaptureModal } from "@/components/marketing/lead-capture-modal";
import {
  BarChart3,
  Package,
  TrendingUp,
  FileBarChart,
  Sparkles,
  ShieldCheck,
} from "lucide-react";

export const metadata: Metadata = {
  title: "Product Demo — DataPulse",
  description:
    "See how DataPulse turns pharma and retail sales data into daily decision-ready intelligence.",
};

const DEMO_FEATURES = [
  {
    icon: BarChart3,
    title: "Executive Revenue Dashboard",
    description:
      "Total revenue, day-over-day trends, top products and branches — all from one executive overview. Drillable by date range, branch, and product category.",
  },
  {
    icon: Package,
    title: "Inventory & Expiry Monitoring",
    description:
      "Stock level tracking, stockout risk alerts, and batch expiry timelines. Surface the items that need action before they become problems.",
  },
  {
    icon: TrendingUp,
    title: "Branch Performance Comparison",
    description:
      "Compare revenue, volume, and efficiency across all branches. Identify outliers and trend shifts at the regional and site level.",
  },
  {
    icon: Sparkles,
    title: "Explainable Insights & Anomalies",
    description:
      "DataPulse flags what changed and explains why — anomaly detection with context so teams know where to look next.",
  },
  {
    icon: FileBarChart,
    title: "Scheduled Reporting",
    description:
      "Daily briefings and monthly roll-ups delivered automatically. From executive summaries to operations team outputs.",
  },
  {
    icon: ShieldCheck,
    title: "Data Quality & Pipeline Health",
    description:
      "Every data import goes through automated cleaning, deduplication, and validation. Pipeline health is visible in the dashboard at all times.",
  },
] as const;

export default function DemoPage() {
  return (
    <>
      <SectionWrapper>
        <div className="mx-auto max-w-3xl text-center">
          <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.26em] text-accent/80">
            Product demo
          </p>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
            See DataPulse in action
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-text-secondary">
            DataPulse turns messy pharma and retail sales data into a daily
            decision-ready operating view — in hours, not weeks.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <LeadCaptureModal trigger="Request a Live Demo" />
            <Link
              href="/#pilot-access"
              className="rounded-full border border-white/15 bg-white/5 px-8 py-3.5 text-sm font-semibold text-text-primary transition-colors hover:bg-white/10"
            >
              View Pilot Options
            </Link>
          </div>
        </div>
      </SectionWrapper>

      <SectionWrapper>
        <div className="mb-10 text-center">
          <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">
            What you&apos;ll see in the dashboard
          </h2>
        </div>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {DEMO_FEATURES.map(({ icon: Icon, title, description }) => (
            <div
              key={title}
              className="viz-panel rounded-[1.5rem] p-6"
            >
              <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-accent/10">
                <Icon className="h-5 w-5 text-accent" />
              </div>
              <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-text-secondary">{description}</p>
            </div>
          ))}
        </div>
      </SectionWrapper>

      <SectionWrapper>
        <div className="viz-panel rounded-[2rem] p-8 text-center sm:p-12">
          <h2 className="text-2xl font-bold sm:text-3xl">
            Ready to see it with your own data?
          </h2>
          <p className="mx-auto mt-4 max-w-lg text-text-secondary">
            Most teams see their first useful dashboard within hours of uploading their
            first file. We can set up a pilot in a focused workflow to prove value quickly.
          </p>
          <div className="mt-8">
            <LeadCaptureModal trigger="Request Pilot Access" />
          </div>
        </div>
      </SectionWrapper>
    </>
  );
}
