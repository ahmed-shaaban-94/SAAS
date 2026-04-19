import { withSentryConfig } from "@sentry/nextjs";
import createNextIntlPlugin from "next-intl/plugin";

// Load @next/bundle-analyzer lazily so `next lint` / `next build` still work
// when the optional dev dependency is missing (fresh clones, CI lint job,
// minimal installs). Falls back to an identity wrapper.
async function resolveBundleAnalyzer() {
  try {
    const mod = await import("@next/bundle-analyzer");
    return mod.default({ enabled: process.env.ANALYZE === "true" });
  } catch {
    return (cfg) => cfg;
  }
}

const withBundleAnalyzer = await resolveBundleAnalyzer();

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  experimental: {
    // Tree-shake named exports from large icon/chart packages so only used
    // symbols are included in the client bundle (verified with ANALYZE=true).
    optimizePackageImports: ["lucide-react", "recharts", "date-fns"],
  },
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
  async redirects() {
    return [
      // v2 cutover: preview URLs now point to the production routes.
      { source: "/dashboard-v2", destination: "/dashboard", permanent: true },
      { source: "/inventory-v2", destination: "/inventory", permanent: true },
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

// Build the final config:
// - Always: bundle analyzer wrapper (no-op unless ANALYZE=true)
// - Conditionally: Sentry wrapper (only when DSN is set)
const baseConfig = process.env.NEXT_PUBLIC_SENTRY_DSN
  ? sentryConfig
  : withNextIntl(nextConfig);

export default withBundleAnalyzer(baseConfig);
