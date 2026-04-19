import V2Layout from "@/components/dashboard-v2/v2-layout";

/**
 * /sites layout — wraps ONLY the root-level /sites/[key]/ detail page.
 * The parent list page /sites stays in (app)/sites/.
 */
export default function SitesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <V2Layout>{children}</V2Layout>;
}
