import { Sidebar } from "@/components/layout/sidebar";
import { Providers } from "@/components/providers";
import { ErrorBoundary } from "@/components/error-boundary";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <Providers>
      <ErrorBoundary>
        <Sidebar />
        <main className="min-h-screen p-4 lg:ml-60 lg:p-6">{children}</main>
      </ErrorBoundary>
    </Providers>
  );
}
