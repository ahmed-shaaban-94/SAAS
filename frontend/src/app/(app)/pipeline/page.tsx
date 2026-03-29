import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { PipelineOverview } from "@/components/pipeline/pipeline-overview";
import { RunHistoryTable } from "@/components/pipeline/run-history-table";
import { TriggerButton } from "@/components/pipeline/trigger-button";

export default function PipelinePage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <div className="flex items-center justify-between">
        <Header title="Pipeline Status" description="Monitor ETL pipeline runs and data quality" />
        <TriggerButton />
      </div>
      <PipelineOverview />
      <div className="mt-6">
        <RunHistoryTable />
      </div>
    </PageTransition>
  );
}
