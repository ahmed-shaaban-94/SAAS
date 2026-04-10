import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { LoadingCard, SkeletonCard, AnimatedCard, CardPresence } from "@/components/loading-card";

describe("LoadingCard", () => {
  it("renders with default 3 shimmer lines", () => {
    const { container } = render(<LoadingCard />);
    const shimmerLines = container.querySelectorAll(".shimmer-line");
    // 2 fixed shimmer lines + 3 dynamic = 5
    expect(shimmerLines.length).toBe(5);
  });

  it("renders custom number of lines", () => {
    const { container } = render(<LoadingCard lines={5} />);
    const shimmerLines = container.querySelectorAll(".shimmer-line");
    // 2 fixed + 5 dynamic = 7
    expect(shimmerLines.length).toBe(7);
  });

  it("applies custom className", () => {
    const { container } = render(<LoadingCard className="w-full" />);
    expect(container.firstChild).toHaveClass("w-full");
  });

  it("has animation class", () => {
    const { container } = render(<LoadingCard />);
    expect(container.firstChild).toHaveClass("animate-fade-in");
  });
});

describe("SkeletonCard", () => {
  it("is an alias for LoadingCard", () => {
    expect(SkeletonCard).toBe(LoadingCard);
  });
});

describe("AnimatedCard", () => {
  it("renders children without layoutId", () => {
    render(<AnimatedCard><span>Content</span></AnimatedCard>);
    expect(screen.getByText("Content")).toBeInTheDocument();
  });

  it("applies className", () => {
    const { container } = render(<AnimatedCard className="test-class"><span>OK</span></AnimatedCard>);
    expect(container.firstChild).toHaveClass("test-class");
  });
});

describe("CardPresence", () => {
  it("is exported and renders children", () => {
    render(<CardPresence><div>child</div></CardPresence>);
    expect(screen.getByText("child")).toBeInTheDocument();
  });
});
