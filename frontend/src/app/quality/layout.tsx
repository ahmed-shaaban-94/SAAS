import V2Layout from "@/components/dashboard-v2/v2-layout";

/** /quality layout — forwards to the shared V2Layout. */
export default function QualityLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <V2Layout>{children}</V2Layout>;
}
