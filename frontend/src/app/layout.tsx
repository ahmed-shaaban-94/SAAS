import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import { isRtl } from "@/i18n/config";
import type { Locale } from "@/i18n/config";
import { PWARegister } from "@/components/pwa-register";
import "@fontsource-variable/inter";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || "https://datapulse.dev"),
  title: {
    default: "DataPulse - Turn Raw Sales Data into Revenue Intelligence",
    template: "%s | DataPulse",
  },
  description:
    "Import, clean, analyze, and visualize your sales data with an automated medallion pipeline. AI-powered insights, real-time dashboards, and enterprise-grade quality gates.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "DataPulse",
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    siteName: "DataPulse",
  },
  twitter: {
    card: "summary_large_image",
  },
  icons: {
    icon: "/favicon.ico",
    apple: "/icons/icon-192.png",
  },
  other: {
    "mobile-web-app-capable": "yes",
  },
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  // Intentionally do NOT set maximumScale: pinch-zoom must stay enabled
  // for WCAG 2.1 SC 1.4.4 compliance.
  viewportFit: "cover" as const,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F6F8FA" },
    { media: "(prefers-color-scheme: dark)", color: "#0D1117" },
  ],
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = (await getLocale()) as Locale;
  const messages = await getMessages();
  const dir = isRtl(locale) ? "rtl" : "ltr";

  return (
    <html lang={locale} dir={dir} suppressHydrationWarning>
      <body className="bg-page font-sans text-text-primary antialiased">
        <a href="#main-content" className="skip-to-content">
          Skip to main content
        </a>
        <NextIntlClientProvider messages={messages}>
          <PWARegister />
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
