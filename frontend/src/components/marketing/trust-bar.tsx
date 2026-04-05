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
    <section className="border-t border-b border-border/50 bg-card/20 py-8 overflow-hidden">
      <p className="text-center text-sm text-text-secondary mb-6">
        Trusted by{" "}
        <span className="text-text-primary font-semibold">500+</span> data
        teams worldwide
      </p>
      <div className="relative">
        <div className="trust-scroll">
          {items.map((name, i) => (
            <span
              key={`${name}-${i}`}
              className="text-lg font-semibold text-text-secondary/40 whitespace-nowrap select-none"
            >
              {name}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
