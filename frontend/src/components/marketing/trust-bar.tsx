export function TrustBar() {
  const USE_CASES = [
    "Branch performance",
    "Product movement",
    "Stock visibility",
    "Expiry exposure",
    "Supplier workflows",
    "Purchasing operations",
  ];

  return (
    <section className="border-y border-white/10 bg-white/[0.03] py-8 backdrop-blur-sm">
      <p className="mb-5 text-center text-sm font-medium text-text-secondary">
        Built for teams that manage:
      </p>
      <div className="mx-auto flex max-w-4xl flex-wrap justify-center gap-3 px-4">
        {USE_CASES.map((item) => (
          <span
            key={item}
            className="rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-sm text-text-secondary/80"
          >
            {item}
          </span>
        ))}
      </div>
    </section>
  );
}
