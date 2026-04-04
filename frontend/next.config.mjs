import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  experimental: {
    optimizePackageImports: ["lucide-react", "recharts", "date-fns"],
  },
  // Redirect root to the static landing page (server-side 308)
  async redirects() {
    return [
      {
        source: "/",
        destination: "/landing.html",
        permanent: true,
      },
    ];
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

export default withNextIntl(nextConfig);
