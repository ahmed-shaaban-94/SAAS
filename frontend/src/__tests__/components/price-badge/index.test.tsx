import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PriceBadge } from "@/components/price-badge";

describe("PriceBadge", () => {
  it("renders USD by default locale", () => {
    render(<PriceBadge minorUnits={4900} currency="USD" locale="en" />);
    expect(screen.getByText(/\$49\.00/)).toBeInTheDocument();
  });

  it("renders EGP in ar locale", () => {
    render(<PriceBadge minorUnits={149900} currency="EGP" locale="ar" />);
    expect(screen.getByText(/١٬?٤٩٩|1,499/)).toBeInTheDocument();
  });

  it("appends per-month suffix when monthly=true", () => {
    render(<PriceBadge minorUnits={4900} currency="USD" locale="en" monthly />);
    expect(screen.getByText(/\/mo/i)).toBeInTheDocument();
  });
});
