import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { GoalsOverview } from "@/components/goals/goals-overview";

export default function GoalsPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Goals & Targets"
        description="Set and track sales targets across the organization"
      />
      <GoalsOverview />
    </PageTransition>
  );
}
