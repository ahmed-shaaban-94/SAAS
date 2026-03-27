import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";
import { Providers } from "@/components/providers";
import { ErrorBoundary } from "@/components/error-boundary";

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
          <ErrorBoundary>
            <Sidebar />
            <main className="min-h-screen p-4 lg:ml-60 lg:p-6">{children}</main>
          </ErrorBoundary>
        </Providers>
      </body>
    </html>
  );
}
