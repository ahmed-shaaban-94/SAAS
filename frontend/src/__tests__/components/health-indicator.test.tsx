import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../test-utils";
import { HealthIndicator } from "@/components/layout/health-indicator";

describe("HealthIndicator", () => {
  it("shows 'API Connected' when healthy", async () => {
    renderWithProviders(<HealthIndicator />);
    await waitFor(() => {
      expect(screen.getByText("API Connected")).toBeInTheDocument();
    });
  });

  it("renders a green status dot when healthy", async () => {
    const { container } = renderWithProviders(<HealthIndicator />);
    await waitFor(() => {
      const dot = container.querySelector("span.bg-accent");
      expect(dot).toBeInTheDocument();
    });
  });
});
