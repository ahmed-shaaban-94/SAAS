import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "DataPulse — Embedded",
};

/**
 * Minimal layout for embed pages — no sidebar, no providers, no auth.
 */
export default function EmbedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
