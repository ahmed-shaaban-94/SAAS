import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { FilterBar } from "@/components/filters/filter-bar";
import { ReturnsOverview } from "@/components/returns/returns-overview";

export default function ReturnsPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Returns Analysis"
        description="Product returns and customer return patterns"
      />
      <FilterBar />
      <ReturnsOverview />
    </PageTransition>
  );
}
