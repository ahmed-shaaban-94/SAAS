import V2Layout from "@/components/dashboard-v2/v2-layout";

export default function InsightsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <V2Layout>{children}</V2Layout>;
}
