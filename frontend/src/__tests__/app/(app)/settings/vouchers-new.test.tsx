import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import NewVoucherPage from "@/app/(app)/settings/vouchers/new/page";

// The shared setup.ts mocks next/navigation.useRouter but returns a fresh mock
// object per import; we re-mock here so we can spy on .push().
const pushMock = vi.fn();
vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>("next/navigation");
  return {
    ...actual,
    useRouter: () => ({
      push: pushMock,
      replace: vi.fn(),
      back: vi.fn(),
      prefetch: vi.fn(),
    }),
    usePathname: () => "/settings/vouchers/new",
    useSearchParams: () => new URLSearchParams(),
  };
});

beforeEach(() => {
  pushMock.mockReset();
});

describe("NewVoucherPage", () => {
  it("renders all required form fields", () => {
    render(<NewVoucherPage />);
    expect(screen.getByLabelText(/code/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/value/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/max uses/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create voucher/i })).toBeInTheDocument();
  });

  it("blocks submission and shows errors when code and value are invalid", async () => {
    const user = userEvent.setup();
    render(<NewVoucherPage />);

    // Submit without filling anything — validator should flag both fields.
    await user.click(screen.getByRole("button", { name: /create voucher/i }));

    await waitFor(() => {
      expect(screen.getByText(/code must be 3-64 characters/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/value must be greater than zero/i)).toBeInTheDocument();
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("rejects percent values above 100", async () => {
    const user = userEvent.setup();
    render(<NewVoucherPage />);

    await user.type(screen.getByLabelText(/code/i), "TEST123");
    await user.click(screen.getByLabelText(/percent/i));
    await user.type(screen.getByLabelText(/value/i), "150");

    await user.click(screen.getByRole("button", { name: /create voucher/i }));

    await waitFor(() => {
      expect(screen.getByText(/percent value must be ≤ 100/i)).toBeInTheDocument();
    });
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("submits valid payload and navigates on success", async () => {
    const user = userEvent.setup();
    render(<NewVoucherPage />);

    await user.type(screen.getByLabelText(/code/i), "WELCOME");
    await user.type(screen.getByLabelText(/value/i), "15");

    await user.click(screen.getByRole("button", { name: /create voucher/i }));

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/settings/vouchers");
    });
  });

  it("upper-cases the code as the user types", async () => {
    const user = userEvent.setup();
    render(<NewVoucherPage />);
    const codeInput = screen.getByLabelText(/code/i) as HTMLInputElement;
    await user.type(codeInput, "welcome");
    expect(codeInput.value).toBe("WELCOME");
  });
});
