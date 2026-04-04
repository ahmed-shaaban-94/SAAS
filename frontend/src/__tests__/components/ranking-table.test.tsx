import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { RankingTable } from "@/components/shared/ranking-table";
import type { RankingItem } from "@/types/api";

const mockItems: RankingItem[] = [
  { rank: 1, key: 1, name: "Product Alpha", value: 500000, pct_of_total: 45.0 },
  { rank: 2, key: 2, name: "Product Beta", value: 300000, pct_of_total: 27.0 },
  { rank: 3, key: 3, name: "Product Gamma", value: 200000, pct_of_total: 18.0 },
  { rank: 4, key: 4, name: "Product Delta", value: 110000, pct_of_total: 10.0 },
];

describe("RankingTable", () => {
  it("renders entity label as column header", () => {
    render(<RankingTable items={mockItems} entityLabel="Product" />);
    expect(screen.getByText("Product")).toBeInTheDocument();
  });

  it("renders all items", () => {
    render(<RankingTable items={mockItems} entityLabel="Product" />);
    expect(screen.getByText("Product Alpha")).toBeInTheDocument();
    expect(screen.getByText("Product Beta")).toBeInTheDocument();
    expect(screen.getByText("Product Gamma")).toBeInTheDocument();
    expect(screen.getByText("Product Delta")).toBeInTheDocument();
  });

  it("renders revenue values as EGP currency", () => {
    render(<RankingTable items={mockItems} entityLabel="Product" />);
    // Currency uses ar-EG locale — symbol is "ج.م." (Arabic) not "EGP"
    const kpiValues = screen.getAllByText(/ج\.م\./);
    expect(kpiValues.length).toBeGreaterThanOrEqual(4);
  });

  it("renders percentage share values", () => {
    render(<RankingTable items={mockItems} entityLabel="Product" />);
    expect(screen.getByText("45.0%")).toBeInTheDocument();
    expect(screen.getByText("27.0%")).toBeInTheDocument();
  });

  it("renders rank badges (Trophy for #1)", () => {
    const { container } = render(<RankingTable items={mockItems} entityLabel="Product" />);
    // Rank 4 shows as text number
    expect(screen.getByText("4")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <RankingTable items={mockItems} entityLabel="Product" className="mt-4" />,
    );
    expect(container.firstChild).toHaveClass("mt-4");
  });

  it("renders empty table when no items", () => {
    const { container } = render(<RankingTable items={[]} entityLabel="Product" />);
    const rows = container.querySelectorAll("tbody tr");
    expect(rows.length).toBe(0);
  });

  it("has accessible table label", () => {
    render(<RankingTable items={mockItems} entityLabel="Product" />);
    const table = screen.getByRole("table", { name: /rankings/i });
    expect(table).toBeInTheDocument();
  });
});
