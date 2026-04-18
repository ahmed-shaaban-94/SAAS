import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { WhyChanged, type WhyChangedData } from "@/components/why-changed/why-changed";
import { WhyChangedTrigger } from "@/components/why-changed/why-changed-trigger";
import {
  buildMtdRevenueWhy,
  buildExpiryExposureWhy,
  buildAvgBasketWhy,
} from "@/components/why-changed/why-changed-data";

// jsdom doesn't implement HTMLDialogElement.showModal() — stub it.
beforeEach(() => {
  if (!HTMLDialogElement.prototype.showModal) {
    HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) {
      this.open = true;
    });
  }
  if (!HTMLDialogElement.prototype.close) {
    HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) {
      this.open = false;
    });
  }
});

const SAMPLE: WhyChangedData = {
  title: "Why did revenue change?",
  subtitle: "Drivers for the last 30 days.",
  totalLabel: "MoM delta",
  totalDisplay: "−EGP 107K · −18%",
  totalSign: "dn",
  drivers: [
    { label: "Stockouts", contribution: -86_000 },
    { label: "Foot traffic", contribution: 24_000 },
    { label: "AOV softness", contribution: -31_000 },
    { label: "Staff changes", contribution: -14_000 },
  ],
  confidence: 0.72,
  actionHref: "/insights",
  actionLabel: "See full breakdown",
};

describe("WhyChanged modal", () => {
  it("renders title, subtitle, and total delta when open", () => {
    render(<WhyChanged open={true} onClose={() => {}} data={SAMPLE} />);
    expect(screen.getByText("Why did revenue change?")).toBeInTheDocument();
    expect(screen.getByText("Drivers for the last 30 days.")).toBeInTheDocument();
    expect(screen.getByText("−EGP 107K · −18%")).toBeInTheDocument();
  });

  it("renders every driver as a list item", () => {
    render(<WhyChanged open={true} onClose={() => {}} data={SAMPLE} />);
    SAMPLE.drivers.forEach((d) => {
      expect(screen.getByText(d.label)).toBeInTheDocument();
    });
  });

  it("shows positive drivers with + sign and negative without", () => {
    render(<WhyChanged open={true} onClose={() => {}} data={SAMPLE} />);
    expect(screen.getByText(/\+24K/)).toBeInTheDocument();
    expect(screen.getByText(/86K/)).toBeInTheDocument();
  });

  it("shows confidence pill when provided", () => {
    render(<WhyChanged open={true} onClose={() => {}} data={SAMPLE} />);
    expect(screen.getByText(/CONFIDENCE 72%/)).toBeInTheDocument();
  });

  it("fires onClose when close button is clicked", () => {
    const onClose = vi.fn();
    render(<WhyChanged open={true} onClose={onClose} data={SAMPLE} />);
    fireEvent.click(screen.getByLabelText("Close"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

describe("WhyChangedTrigger", () => {
  it("renders the child as clickable button with dashed affordance", () => {
    render(
      <WhyChangedTrigger data={SAMPLE}>
        <span>EGP 4.72M</span>
      </WhyChangedTrigger>,
    );
    const btn = screen.getByRole("button", { name: /MoM delta/i });
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveClass("wc-trigger");
  });

  it("opens the modal on click", () => {
    render(
      <WhyChangedTrigger data={SAMPLE}>
        <span>EGP 4.72M</span>
      </WhyChangedTrigger>,
    );
    // Native <dialog> keeps its children in the DOM; check the `open`
    // attribute instead of presence.
    const dialog = document.querySelector("dialog");
    expect(dialog).toBeTruthy();
    expect(dialog!.hasAttribute("open")).toBe(false);

    fireEvent.click(screen.getByRole("button", { name: /MoM delta/i }));
    expect(dialog!.hasAttribute("open")).toBe(true);
    expect(screen.getByText("Drivers for the last 30 days.")).toBeInTheDocument();
  });
});

describe("Why-Changed data builders", () => {
  it("buildMtdRevenueWhy produces an up-sign when growth is positive", () => {
    const d = buildMtdRevenueWhy(4_000_000, 5);
    expect(d.totalSign).toBe("up");
    expect(d.totalDisplay).toMatch(/\+EGP/);
    expect(d.drivers.length).toBeGreaterThan(3);
  });

  it("buildMtdRevenueWhy produces a dn-sign when growth is negative", () => {
    const d = buildMtdRevenueWhy(4_000_000, -12);
    expect(d.totalSign).toBe("dn");
    expect(d.totalDisplay).toMatch(/−EGP/);
  });

  it("buildMtdRevenueWhy flat-signs a null growth pct", () => {
    const d = buildMtdRevenueWhy(4_000_000, null);
    expect(d.totalSign).toBe("flat");
    expect(d.totalDisplay).toBe("—");
  });

  it("buildExpiryExposureWhy all drivers are negative contributions", () => {
    const d = buildExpiryExposureWhy(150_000);
    expect(d.drivers.every((x) => x.contribution < 0)).toBe(true);
  });

  it("buildAvgBasketWhy returns mixed signs (positive and negative drivers)", () => {
    const d = buildAvgBasketWhy(3.2);
    const hasPos = d.drivers.some((x) => x.contribution > 0);
    const hasNeg = d.drivers.some((x) => x.contribution < 0);
    expect(hasPos).toBe(true);
    expect(hasNeg).toBe(true);
  });
});
