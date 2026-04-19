import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SWRConfig } from "swr";
import React from "react";
import VouchersPage from "@/app/(app)/settings/vouchers/page";

function renderPage() {
  return render(
    <SWRConfig value={{ dedupingInterval: 0, provider: () => new Map() }}>
      <VouchersPage />
    </SWRConfig>,
  );
}

describe("VouchersPage", () => {
  it("renders the header and a link to create a new voucher", async () => {
    renderPage();
    expect(screen.getByRole("heading", { name: /vouchers/i })).toBeInTheDocument();
    // Multiple "New voucher" anchors (top-right + empty state) may render;
    // assert at least one exists and points to the correct path.
    const links = await screen.findAllByRole("link", { name: /new voucher/i });
    expect(links.length).toBeGreaterThan(0);
    expect(links[0]).toHaveAttribute("href", "/settings/vouchers/new");
  });

  it("renders the voucher table after data loads", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("SUMMER25")).toBeInTheDocument();
    });
    expect(screen.getByText("FLAT50")).toBeInTheDocument();
  });

  it("filters vouchers by status when a tab is clicked", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("SUMMER25")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("tab", { name: /redeemed/i }));

    // Wait for the filtered result — only FLAT50 should remain.
    await waitFor(() => {
      expect(screen.queryByText("SUMMER25")).not.toBeInTheDocument();
    });
    expect(screen.getByText("FLAT50")).toBeInTheDocument();
  });

  it("shows an empty state when the filtered list is empty", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => expect(screen.getByText("SUMMER25")).toBeInTheDocument());

    await user.click(screen.getByRole("tab", { name: /void/i }));

    await waitFor(() => {
      expect(screen.getByText(/no vouchers yet/i)).toBeInTheDocument();
    });
  });
});
