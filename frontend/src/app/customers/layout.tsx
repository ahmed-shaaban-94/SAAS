import V2Layout from "@/components/dashboard-v2/v2-layout";

/**
 * /customers layout — wraps ONLY the root-level /customers/[key]/ detail
 * page. The parent list page /customers stays in (app)/customers/ and
 * inherits the (app) layout. Different URL leaves, no conflict.
 */
export default function CustomersLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <V2Layout>{children}</V2Layout>;
}
