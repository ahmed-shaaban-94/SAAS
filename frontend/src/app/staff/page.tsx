import { Header } from "@/components/layout/header";
import { FilterBar } from "@/components/filters/filter-bar";
import { StaffOverview } from "@/components/staff/staff-overview";

export default function StaffPage() {
  return (
    <div>
      <Header
        title="Staff Performance"
        description="Sales team performance rankings"
      />
      <FilterBar />
      <StaffOverview />
    </div>
  );
}
