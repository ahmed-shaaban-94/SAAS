"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { AuditLogOverview } from "@/components/audit/audit-log-overview";

export default function AuditPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Audit Log"
        description="Track all API requests and user actions"
      />
      <AuditLogOverview />
    </PageTransition>
  );
}
