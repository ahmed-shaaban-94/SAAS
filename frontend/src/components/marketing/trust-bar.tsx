const TRUST_ITEMS = [
  "Pharma Corp",
  "RetailMax",
  "FoodChain HQ",
  "MediSupply",
  "TechDistro",
  "AgriTrade",
  "BuildMart",
  "AutoParts Pro",
];

export function TrustBar() {
  // Duplicate items for seamless infinite scroll
  const items = [...TRUST_ITEMS, ...TRUST_ITEMS];

  return (
    <section className="overflow-hidden border-y border-white/10 bg-white/[0.03] py-8 backdrop-blur-sm">
      <p className="mb-6 text-center text-sm text-text-secondary">
        Trusted by{" "}
        <span className="text-text-primary font-semibold">500+</span> data
        teams worldwide
      </p>
      <div className="relative">
        <div className="trust-scroll">
          {items.map((name, i) => (
            <span
              key={`${name}-${i}`}
              className="select-none whitespace-nowrap text-lg font-semibold text-text-secondary/50"
            >
              {name}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
