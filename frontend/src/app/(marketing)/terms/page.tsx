import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "DataPulse terms of service - usage terms and conditions.",
  alternates: { canonical: "/terms" },
};

export default function TermsPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 pb-16 pt-32 sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold sm:text-4xl">Terms of Service</h1>
      <p className="mt-2 text-sm text-text-secondary">
        Last updated: {new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
      </p>

      <div className="mt-8 space-y-8 text-sm leading-relaxed text-text-secondary">
        <section>
          <h2 className="mb-3 text-lg font-semibold text-text-primary">
            1. Acceptance of Terms
          </h2>
          <p>
            By accessing or using DataPulse, you agree to be bound by these
            Terms of Service. If you do not agree to these terms, do not use our
            service.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-text-primary">
            2. Description of Service
          </h2>
          <p>
            DataPulse is a data analytics platform that provides sales data
            import, cleaning, transformation, and visualization services. The
            platform includes automated data pipelines, quality gates, AI-powered
            insights, and interactive dashboards.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-text-primary">
            3. User Accounts
          </h2>
          <p>
            You are responsible for maintaining the confidentiality of your
            account credentials. You agree to notify us immediately of any
            unauthorized use. We reserve the right to suspend accounts that
            violate these terms.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-text-primary">
            4. Data Ownership
          </h2>
          <p>
            You retain full ownership of all data you upload to DataPulse. We do
            not claim any intellectual property rights over your data. You grant
            us a limited license to process your data solely for providing the
            service.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-text-primary">
            5. Acceptable Use
          </h2>
          <p>
            You agree not to: upload malicious files, attempt to access other
            users&apos; data, reverse-engineer the platform, or use the service for
            any illegal purpose. We reserve the right to terminate accounts that
            violate these policies.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-text-primary">
            6. Service Availability
          </h2>
          <p>
            We strive for high availability but do not guarantee uninterrupted
            service. We may perform maintenance with reasonable notice. The free
            tier is provided as-is without service level guarantees.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-text-primary">
            7. Limitation of Liability
          </h2>
          <p>
            DataPulse is provided &quot;as is&quot; without warranty of any kind. We are
            not liable for any indirect, incidental, or consequential damages
            arising from use of the service. Our total liability shall not
            exceed the amount paid by you in the twelve months preceding the
            claim.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-text-primary">
            8. Changes to Terms
          </h2>
          <p>
            We may update these terms from time to time. We will notify users of
            material changes via email or in-app notification. Continued use
            after changes constitutes acceptance of the updated terms.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-text-primary">
            9. Contact
          </h2>
          <p>
            For questions about these terms, contact us at{" "}
            <a href="mailto:legal@datapulse.dev" className="text-accent hover:underline">
              legal@datapulse.dev
            </a>
            .
          </p>
        </section>
      </div>
    </div>
  );
}
