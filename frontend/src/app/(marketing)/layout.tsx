import { Navbar } from "@/components/marketing/navbar";
import { Footer } from "@/components/marketing/footer";
import { FireBackground } from "@/components/marketing/fire-background";

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[100] focus:rounded-lg focus:bg-accent focus:px-4 focus:py-2 focus:text-page"
      >
        Skip to content
      </a>
      <FireBackground />
      <Navbar />
      <main id="main-content" className="relative z-10">
        {children}
      </main>
      <Footer />
    </>
  );
}
