import V2Layout from "@/components/dashboard-v2/v2-layout";

/**
 * /products layout — wraps ONLY the root-level /products/[key]/ detail
 * page. The parent list page /products stays in (app)/products/.
 */
export default function ProductsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <V2Layout>{children}</V2Layout>;
}
