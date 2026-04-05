"use client";

import Link from "next/link";
import { TypingSubtitle } from "./typing-subtitle";

export function HeroSection() {
  return (
    <section className="relative overflow-hidden px-4 pb-16 pt-32 sm:px-6 md:pb-24 md:pt-40 lg:px-8">
      {/* Background glow blobs */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute left-1/2 top-0 h-[600px] w-[800px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent/10 blur-[100px]" />
        <div className="absolute right-0 top-1/3 h-[400px] w-[400px] rounded-full bg-chart-blue/10 blur-[100px]" />
      </div>

      <div className="relative mx-auto max-w-6xl">
        <div className="mx-auto max-w-3xl text-center">
          {/* Badge */}
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-accent/20 bg-accent/5 px-4 py-1.5 text-sm text-accent">
            <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />
            Now in public beta
          </div>

          {/* Headline */}
          <h1 className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl md:text-6xl">
            Turn Raw Sales Data into{" "}
            <span className="gradient-text-animated">Revenue Intelligence</span>
          </h1>

          {/* Typing subtitle */}
          <p className="mx-auto mt-6 max-w-2xl text-lg text-text-secondary sm:text-xl min-h-[60px] sm:min-h-0">
            <TypingSubtitle
              text="Import, clean, analyze, and visualize your sales data with an automated medallion pipeline. From Excel chaos to actionable dashboards in minutes."
              speed={25}
            />
          </p>

          {/* CTAs */}
          <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              href="/dashboard"
              className="cta-shimmer w-full rounded-lg bg-accent px-8 py-3 text-center text-sm font-semibold text-page transition-all hover:bg-accent/90 sm:w-auto"
            >
              Start Free Trial
            </Link>
            <a
              href="#how-it-works"
              className="w-full rounded-lg border border-border bg-card/50 backdrop-blur px-8 py-3 text-center text-sm font-semibold text-text-primary transition-colors hover:bg-card sm:w-auto"
            >
              See How It Works
            </a>
          </div>
        </div>

        {/* Dashboard mockup — floating */}
        <div className="mx-auto mt-16 max-w-4xl float-card">
          <div className="rounded-xl border border-border bg-card/80 backdrop-blur-sm p-4 shadow-2xl relative overflow-hidden">
            {/* Top accent bar */}
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-accent via-chart-amber to-chart-blue" />

            {/* Title bar dots */}
            <div className="mb-4 flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-growth-red/60" />
              <div className="h-3 w-3 rounded-full bg-chart-amber/60" />
              <div className="h-3 w-3 rounded-full bg-growth-green/60" />
              <span className="ml-2 text-xs text-text-secondary">
                Data Pulse Dashboard
              </span>
            </div>

            {/* KPI row */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                { label: "Total Revenue", value: "EGP 4.2M", change: "+12.5%" },
                { label: "Orders", value: "23,847", change: "+8.3%" },
                { label: "Customers", value: "1,245", change: "+15.2%" },
                { label: "Avg. Order", value: "EGP 176", change: "+4.1%" },
              ].map((kpi) => (
                <div
                  key={kpi.label}
                  className="rounded-lg border border-border/50 bg-page/50 p-3"
                >
                  <p className="text-xs text-text-secondary">{kpi.label}</p>
                  <p className="mt-1 text-lg font-bold">{kpi.value}</p>
                  <p className="text-xs text-growth-green">{kpi.change}</p>
                </div>
              ))}
            </div>

            {/* Chart mockup */}
            <div className="mt-4 rounded-lg border border-border/50 bg-page/50 p-4">
              <p className="mb-3 text-xs text-text-secondary">Revenue Trend</p>
              <div className="flex h-32 items-end gap-1.5">
                {[40, 55, 35, 65, 50, 75, 60, 85, 70, 90, 80, 95].map(
                  (h, i) => (
                    <div
                      key={i}
                      className="flex-1 rounded-t bg-gradient-to-t from-accent/40 to-accent/80 transition-all"
                      style={{ height: `${h}%` }}
                    />
                  )
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
