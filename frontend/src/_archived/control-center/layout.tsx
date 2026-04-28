import V2Layout from "@/components/dashboard-v2/v2-layout";

/** /control-center layout — covers parent + 5 child pages. */
export default function ControlCenterLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <V2Layout>{children}</V2Layout>;
}
