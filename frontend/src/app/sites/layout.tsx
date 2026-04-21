import V2Layout from "@/components/dashboard-v2/v2-layout";

/**
 * /sites layout — forwards to the shared V2Layout.
 *
 * The /sites/[key] detail page stays inside the (app) route group
 * until that drill-down is migrated in a follow-up.
 */
export default function SitesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <V2Layout>{children}</V2Layout>;
}
