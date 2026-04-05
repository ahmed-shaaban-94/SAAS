import { Navbar } from "@/components/marketing/navbar";
import { Footer } from "@/components/marketing/footer";
import { NetworkCanvas } from "@/components/marketing/network-canvas";
import { StickyCTA } from "@/components/marketing/sticky-cta";

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div
      className="marketing-dark min-h-screen"
      style={{ background: "#0D1117", color: "#E6EDF3" }}
    >
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[100] focus:rounded-lg focus:bg-accent focus:px-4 focus:py-2 focus:text-page"
      >
        Skip to content
      </a>
      <NetworkCanvas />
      <Navbar />
      <main id="main-content" className="relative z-10">{children}</main>
      <StickyCTA />
      <Footer />
    </div>
  );
}
