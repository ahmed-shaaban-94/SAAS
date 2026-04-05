import * as Sentry from "@sentry/nextjs";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || "development",
    tracesSampleRate: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT === "production" ? 0.1 : 1.0,
    debug: false,
  });
}
