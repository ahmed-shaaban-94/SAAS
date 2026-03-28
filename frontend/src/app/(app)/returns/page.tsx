import { Header } from "@/components/layout/header";
import { FilterBar } from "@/components/filters/filter-bar";
import { ReturnsOverview } from "@/components/returns/returns-overview";

export default function ReturnsPage() {
  return (
    <div>
      <Header
        title="Returns Analysis"
        description="Product returns and customer return patterns"
      />
      <FilterBar />
      <ReturnsOverview />
    </div>
  );
}
