import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { FilterBar } from "@/components/filters/filter-bar";
import { SiteOverview } from "@/components/sites/site-overview";

export default function SitesPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Site Comparison"
        description="Performance across pharmacy locations"
      />
      <FilterBar />
      <SiteOverview />
    </PageTransition>
  );
}
