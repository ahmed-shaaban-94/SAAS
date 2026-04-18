import type { Metadata } from "next";
import { Fraunces, JetBrains_Mono } from "next/font/google";

const fraunces = Fraunces({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-fraunces",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Dashboard v2 — DataPulse",
  description: "Preview of the hybrid operations dashboard design.",
};

export default function DashboardV2Layout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <div className={`${fraunces.variable} ${jetbrainsMono.variable}`}>{children}</div>;
}
