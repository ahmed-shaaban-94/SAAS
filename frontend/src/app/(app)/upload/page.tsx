"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { UploadOverview } from "@/components/upload/upload-overview";

export default function UploadPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Import Data"
        description="Upload Excel or CSV files for pipeline processing"
      />
      <UploadOverview />
    </PageTransition>
  );
}
