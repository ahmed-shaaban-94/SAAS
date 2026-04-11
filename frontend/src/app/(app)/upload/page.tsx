"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { DataOpsCommandBar } from "@/components/data-ops/command-bar";
import { UploadOverview } from "@/components/upload/upload-overview";

export default function UploadPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Import Data"
        description="Upload files, validate, and launch the pipeline"
      />
      <DataOpsCommandBar />
      <UploadOverview />
    </PageTransition>
  );
}
