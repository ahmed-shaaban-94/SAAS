import V2Layout from "@/components/dashboard-v2/v2-layout";

/**
 * /inventory layout — forwards to the shared V2Layout.
 *
 * The /inventory/[drug_code] detail page stays inside the (app) route
 * group (it is a drill-down, not an overview surface). Different URL
 * leaves so no Next.js route conflict.
 */
export default function InventoryLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <V2Layout>{children}</V2Layout>;
}
