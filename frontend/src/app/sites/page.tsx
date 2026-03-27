import { Header } from "@/components/layout/header";
import { FilterBar } from "@/components/filters/filter-bar";
import { SiteOverview } from "@/components/sites/site-overview";

export default function SitesPage() {
  return (
    <div>
      <Header
        title="Site Comparison"
        description="Performance across pharmacy locations"
      />
      <FilterBar />
      <SiteOverview />
    </div>
  );
}
