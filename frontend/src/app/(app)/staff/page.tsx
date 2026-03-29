import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { FilterBar } from "@/components/filters/filter-bar";
import { StaffOverview } from "@/components/staff/staff-overview";

export default function StaffPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Staff Performance"
        description="Sales team performance rankings"
      />
      <FilterBar />
      <StaffOverview />
    </PageTransition>
  );
}
