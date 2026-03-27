import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";
import { Providers } from "@/components/providers";

export const metadata: Metadata = {
  title: "DataPulse",
  description: "Sales analytics dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-page text-text-primary antialiased">
        <Providers>
          <Sidebar />
          <main className="ml-60 min-h-screen p-6">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
