import { Header } from "@/components/layout/header";
import { FilterBar } from "@/components/filters/filter-bar";
import { ProductOverview } from "@/components/products/product-overview";

export default function ProductsPage() {
  return (
    <div>
      <Header
        title="Product Analytics"
        description="Top performing products by revenue"
      />
      <FilterBar />
      <ProductOverview />
    </div>
  );
}
