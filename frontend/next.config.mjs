import { withSentryConfig } from "@sentry/nextjs";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  experimental: {
    scrollRestoration: true,
    optimizePackageImports: [
      "lucide-react",
      "recharts",
      "date-fns",
      "framer-motion",
      "react-day-picker",
      "@radix-ui/react-popover",
      "@radix-ui/react-dialog",
      "@radix-ui/react-dropdown-menu",
      "@radix-ui/react-tooltip",
    ],
  },
  compress: true,
  // Proxy /api/v1/* and /health to the FastAPI backend.
  // This lets NEXT_PUBLIC_API_URL stay empty (same-origin requests from the
  // browser) while the Next.js server forwards the calls to the API container.
  async rewrites() {
    const apiOrigin = process.env.INTERNAL_API_URL || "http://api:8000";
    return [
      {
        source: "/health",
        destination: `${apiOrigin}/health`,
      },
      {
        source: "/api/v1/:path*",
        destination: `${apiOrigin}/api/v1/:path*`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "X-DNS-Prefetch-Control",
            value: "on",
          },
        ],
      },
      {
        // Cache static marketing assets
        source: "/opengraph-image",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=86400, stale-while-revalidate=43200",
          },
        ],
      },
      {
        // Cache static assets (fonts, images, etc.)
        source: "/(.*)\\.(woff2|woff|ttf|ico|png|jpg|jpeg|svg|webp)",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
      {
        // Short cache for API proxy responses with stale-while-revalidate
        source: "/api/v1/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "private, max-age=30, stale-while-revalidate=60",
          },
        ],
      },
    ];
  },
};

const sentryConfig = withSentryConfig(withNextIntl(nextConfig), {
  // Suppress source map upload logs in CI
  silent: true,
  // Hide source maps from client bundles
  hideSourceMaps: true,
  // Disable telemetry
  telemetry: false,
});

// Only wrap with Sentry if DSN is configured
export default process.env.NEXT_PUBLIC_SENTRY_DSN
  ? sentryConfig
  : withNextIntl(nextConfig);
