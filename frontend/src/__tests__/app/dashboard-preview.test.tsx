import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

// Stub DashboardGrid so this page test stays focused on the shell
// chrome (title, back link, aria-labels) rather than the 10 widgets.
vi.mock("@/components/dashboard/new/dashboard-grid", () => ({
  DashboardGrid: () => <div data-testid="dashboard-grid-new" />,
}));

import DashboardPreviewPage from "@/app/dashboard/preview/page";

describe("/dashboard/preview page", () => {
  it("renders the design-recreation heading", () => {
    render(<DashboardPreviewPage />);
    expect(
      screen.getByRole("heading", { name: /Daily Operations Overview/i }),
    ).toBeInTheDocument();
  });

  it("links back to the production /dashboard route", () => {
    render(<DashboardPreviewPage />);
    const back = screen.getByRole("link", {
      name: /Back to current dashboard/i,
    });
    expect(back).toHaveAttribute("href", "/dashboard");
  });

  it("links to the epic issue for context", () => {
    render(<DashboardPreviewPage />);
    const epic = screen.getByRole("link", { name: /epic #501/i });
    expect(epic).toHaveAttribute(
      "href",
      "https://github.com/ahmed-shaaban-94/Data-Pulse/issues/501",
    );
    expect(epic).toHaveAttribute("target", "_blank");
  });

  it("mounts the DashboardGrid capstone inside <main>", () => {
    render(<DashboardPreviewPage />);
    const main = screen.getByRole("main");
    expect(main).toContainElement(screen.getByTestId("dashboard-grid-new"));
  });
});
