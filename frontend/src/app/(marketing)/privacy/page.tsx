import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "DataPulse privacy policy - how we handle and protect your data.",
  alternates: { canonical: "/privacy" },
};

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 pb-16 pt-32 sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold sm:text-4xl">Privacy Policy</h1>
      <p className="mt-2 text-sm text-text-secondary">
        Last updated: {new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
      </p>

      <div className="mt-8 space-y-8 text-sm leading-relaxed text-text-secondary">
        <section>
          <h2 className="mb-3 text-lg font-semibold text-text-primary">
            1. Information We Collect
          </h2>
          <p>
            We collect information you provide directly, such as your email
            address when joining our waitlist. We also collect usage data
            including page visits and feature interactions through standard web
            analytics.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-text-primary">
            2. How We Use Your Information
          </h2>
          <p>
            We use your information to provide and improve DataPulse, communicate
            updates and new features, and ensure security and prevent abuse. We
            do not sell your personal data to third parties.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-text-primary">
            3. Data Storage & Security
          </h2>
          <p>
            Your data is stored securely using industry-standard encryption.
            DataPulse implements Row Level Security (RLS) on all database tables,
            ensuring tenant isolation. All credentials are managed via
            environment variables and never stored in source code.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-text-primary">
            4. Data Processing
          </h2>
          <p>
            Sales data you upload is processed through our medallion architecture
            (Bronze, Silver, Gold layers). Data is cleaned, deduplicated, and
            aggregated for analytics purposes. You retain full ownership of your
            data and can request deletion at any time.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-text-primary">
            5. Third-Party Services
          </h2>
          <p>
            DataPulse may use third-party AI services (via OpenRouter) to
            generate insights from your aggregated data. Only anonymized,
            aggregated metrics are sent to AI providers - never raw transaction
            data.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-text-primary">
            6. Your Rights
          </h2>
          <p>
            You have the right to access, correct, or delete your personal data.
            You can request a copy of your data or account deletion by contacting
            us. We will respond to your request within 30 days.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-text-primary">
            7. Contact
          </h2>
          <p>
            For privacy-related questions or requests, please contact us at{" "}
            <a href="mailto:privacy@datapulse.dev" className="text-accent hover:underline">
              privacy@datapulse.dev
            </a>
            .
          </p>
        </section>
      </div>
    </div>
  );
}
