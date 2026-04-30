import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  ReceiptPaper,
  BrandBlock,
} from "@/components/pos/receipts/ReceiptPaper";

describe("ReceiptPaper shell", () => {
  it("renders the paper container with default props (no decoration)", () => {
    render(<ReceiptPaper>body</ReceiptPaper>);
    expect(screen.getByTestId("receipt-paper")).toBeInTheDocument();
    expect(screen.queryByTestId("jagged-edge-top")).not.toBeInTheDocument();
    expect(screen.queryByTestId("jagged-edge-bottom")).not.toBeInTheDocument();
    expect(
      screen.getByTestId("receipt-paper").hasAttribute("data-paper-noise"),
    ).toBe(false);
  });

  it("renders top + bottom jagged edges when jaggedEdges=true", () => {
    render(<ReceiptPaper jaggedEdges>body</ReceiptPaper>);
    expect(screen.getByTestId("jagged-edge-top")).toBeInTheDocument();
    expect(screen.getByTestId("jagged-edge-bottom")).toBeInTheDocument();
  });

  it("never renders jagged edges when flatEdges overrides jaggedEdges", () => {
    render(
      <ReceiptPaper jaggedEdges flatEdges>
        body
      </ReceiptPaper>,
    );
    // flatEdges is the legacy print-preview escape hatch and must win.
    expect(screen.queryByTestId("jagged-edge-top")).not.toBeInTheDocument();
    expect(screen.queryByTestId("jagged-edge-bottom")).not.toBeInTheDocument();
  });

  it("toggles the paper-noise data attribute via paperNoise prop", () => {
    const { rerender } = render(
      <ReceiptPaper paperNoise>body</ReceiptPaper>,
    );
    expect(
      screen.getByTestId("receipt-paper").hasAttribute("data-paper-noise"),
    ).toBe(true);

    rerender(<ReceiptPaper paperNoise={false}>body</ReceiptPaper>);
    expect(
      screen.getByTestId("receipt-paper").hasAttribute("data-paper-noise"),
    ).toBe(false);
  });

  it("never sets data-paper-noise when flatEdges overrides paperNoise", () => {
    // flatEdges is the print-preview escape hatch — it must kill ALL
    // on-screen-only decoration so the preview faithfully matches the
    // printed output. Same semantics as flatEdges + jaggedEdges above.
    render(
      <ReceiptPaper flatEdges paperNoise>
        body
      </ReceiptPaper>,
    );
    expect(
      screen.getByTestId("receipt-paper").hasAttribute("data-paper-noise"),
    ).toBe(false);
  });

  it("jagged edges carry data-torn-edge so the print pipeline strips them", () => {
    render(<ReceiptPaper jaggedEdges>body</ReceiptPaper>);
    // The print-pipeline @media rule keys off [data-torn-edge]. Asserting
    // the attribute presence here makes that contract explicit so future
    // refactors can't accidentally break printed receipts.
    expect(
      screen.getByTestId("jagged-edge-top").hasAttribute("data-torn-edge"),
    ).toBe(true);
    expect(
      screen.getByTestId("jagged-edge-bottom").hasAttribute("data-torn-edge"),
    ).toBe(true);
  });
});

describe("BrandBlock icon variants", () => {
  it("defaults to the legacy 'monogram' variant when no iconVariant is passed", () => {
    render(<BrandBlock siteNameAr="صيدلية تجريبية" />);
    expect(screen.getByTestId("brand-icon-monogram")).toBeInTheDocument();
    expect(
      screen.queryByTestId("brand-icon-heartpulse"),
    ).not.toBeInTheDocument();
    // Wordmark stays unchanged so existing print snapshots match.
    expect(screen.getByText("DataPulse Omni")).toBeInTheDocument();
  });

  it("renders the heartpulse glyph when iconVariant='heartpulse'", () => {
    render(
      <BrandBlock siteNameAr="صيدلية تجريبية" iconVariant="heartpulse" />,
    );
    expect(screen.getByTestId("brand-icon-heartpulse")).toBeInTheDocument();
    expect(screen.queryByTestId("brand-icon-monogram")).not.toBeInTheDocument();
  });
});
