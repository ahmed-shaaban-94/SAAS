import V2Layout from "@/components/dashboard-v2/v2-layout";

/**
 * /dashboard layout — forwards to the shared V2Layout.
 *
 * Full provider stack + shell chrome lives in v2-layout.tsx. Per-page
 * concerns (activeHref, breadcrumbs) are rendered by page.tsx via
 * <DashboardShell>.
 */
export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <V2Layout>{children}</V2Layout>;
}
