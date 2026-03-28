import { SectionWrapper } from "./section-wrapper";
import { WaitlistForm } from "./waitlist-form";

export function CTASection() {
  return (
    <SectionWrapper>
      <div className="rounded-2xl border border-accent/20 bg-gradient-to-br from-accent/5 via-card to-blue/5 p-8 text-center sm:p-12">
        <h2 className="text-3xl font-bold sm:text-4xl">
          Ready to transform your sales data?
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-text-secondary">
          Join the waitlist and be the first to know when DataPulse launches.
          Start turning raw data into revenue intelligence.
        </p>
        <div className="mt-8 flex justify-center">
          <WaitlistForm />
        </div>
      </div>
    </SectionWrapper>
  );
}
