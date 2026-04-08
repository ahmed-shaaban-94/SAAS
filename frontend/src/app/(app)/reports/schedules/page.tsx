"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { ScheduleOverview } from "@/components/reports/schedule-overview";

export default function SchedulesPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Report Schedules"
        description="Manage automated PDF report delivery"
      />
      <ScheduleOverview />
    </PageTransition>
  );
}
