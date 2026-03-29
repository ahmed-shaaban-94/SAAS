import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { FilterBar } from "@/components/filters/filter-bar";
import { ProductOverview } from "@/components/products/product-overview";

export default function ProductsPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Product Analytics"
        description="Top performing products by revenue"
      />
      <FilterBar />
      <ProductOverview />
    </PageTransition>
  );
}
