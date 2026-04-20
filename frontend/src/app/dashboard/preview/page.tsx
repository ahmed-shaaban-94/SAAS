"use client";

/**
 * /dashboard/preview — new-design dashboard preview.
 *
 * Side-by-side cohabitation with the production /dashboard route while
 * the new layout is validated. The v2 dashboard stays at /dashboard;
 * this URL lets reviewers see the #501 design recreation end-to-end
 * against live tenant data.
 *
 * Swap plan (future PR):
 *   1. Capture usage telemetry on /dashboard/preview
 *   2. Gate behind ``DASHBOARD_NEW`` feature flag on /dashboard
 *   3. Delete this route once the flag defaults true
 *
 * This page is intentionally minimal — the DashboardGrid owns all
 * composition; ``/dashboard`` retains its V2 layout providers so the
 * preview doesn't regress on things like horizon / compare / filter
 * contexts until we decide to carry them forward.
 */

import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { DashboardGrid } from "@/components/dashboard/new/dashboard-grid";

export default function DashboardPreviewPage() {
  return (
    <main className="mx-auto w-full max-w-[1400px] px-4 py-6 lg:px-8 lg:py-8">
      <header className="mb-6 flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-text-primary sm:text-2xl">
            Daily Operations Overview
          </h1>
          <p className="mt-1 text-xs text-text-secondary">
            Preview of the new dashboard design (
            <a
              className="underline decoration-dotted hover:decoration-solid"
              href="https://github.com/ahmed-shaaban-94/Data-Pulse/issues/501"
              target="_blank"
              rel="noreferrer"
            >
              epic #501
            </a>
            ). Runs against live tenant data.
          </p>
        </div>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.02] px-3 py-1.5 text-xs font-medium text-text-secondary hover:bg-white/[0.05]"
        >
          <ArrowLeft aria-hidden="true" className="h-3.5 w-3.5" />
          Back to current dashboard
        </Link>
      </header>

      <DashboardGrid />
    </main>
  );
}
