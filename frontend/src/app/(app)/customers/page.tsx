import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { FilterBar } from "@/components/filters/filter-bar";
import { CustomerOverview } from "@/components/customers/customer-overview";

export default function CustomersPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Customer Intelligence"
        description="Top customers by revenue contribution"
      />
      <FilterBar />
      <CustomerOverview />
    </PageTransition>
  );
}
