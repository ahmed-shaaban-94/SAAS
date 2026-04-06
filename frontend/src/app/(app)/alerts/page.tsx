"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { AlertsOverview } from "@/components/alerts/alerts-overview";

export default function AlertsPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Alerts & Notifications"
        description="Configure metric alerts and view notification history"
      />
      <AlertsOverview />
    </PageTransition>
  );
}
