import V2Layout from "@/components/dashboard-v2/v2-layout";

/**
 * The /purchase-orders/[po_number] detail page stays inside the (app)
 * route group as a drill-down; different URL leaves so no conflict.
 */
export default function PurchaseOrdersLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <V2Layout>{children}</V2Layout>;
}
