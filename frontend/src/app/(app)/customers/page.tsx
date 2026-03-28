import { Header } from "@/components/layout/header";
import { FilterBar } from "@/components/filters/filter-bar";
import { CustomerOverview } from "@/components/customers/customer-overview";

export default function CustomersPage() {
  return (
    <div>
      <Header
        title="Customer Intelligence"
        description="Top customers by revenue contribution"
      />
      <FilterBar />
      <CustomerOverview />
    </div>
  );
}
