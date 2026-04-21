import V2Layout from "@/components/dashboard-v2/v2-layout";

/**
 * /products layout — forwards to the shared V2Layout (same pattern as /inventory).
 *
 * The /products/[key] detail page stays inside the (app) route group
 * until that drill-down is migrated in a follow-up.
 */
export default function ProductsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <V2Layout>{children}</V2Layout>;
}
