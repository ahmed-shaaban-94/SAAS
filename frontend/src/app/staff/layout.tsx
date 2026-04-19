import V2Layout from "@/components/dashboard-v2/v2-layout";

/**
 * /staff layout — wraps ONLY the root-level /staff/[key]/ detail page.
 * The parent list page /staff stays in (app)/staff/.
 */
export default function StaffLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <V2Layout>{children}</V2Layout>;
}
