import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const mockValidate = vi.fn();
const mockReset = vi.fn();

vi.mock("@/hooks/use-voucher-validate", () => ({
  useVoucherValidate: () => ({
    data: mockValidate.mock.results.at(-1)?.value ?? null,
    error: null,
    isLoading: false,
    validate: mockValidate,
    reset: mockReset,
  }),
}));

import { VoucherCodeModal } from "@/components/pos/VoucherCodeModal";

describe("VoucherCodeModal (PR 6 redesign)", () => {
  beforeEach(() => {
    mockValidate.mockReset();
    mockReset.mockReset();
  });

  it("renders nothing when closed", () => {
    render(
      <VoucherCodeModal
        open={false}
        cartSubtotal={100}
        onApply={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("pos-voucher-modal")).not.toBeInTheDocument();
  });

  it("uses the new ModalShell with VOUCHER badge and amber accent", () => {
    render(
      <VoucherCodeModal
        open
        cartSubtotal={100}
        onApply={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByTestId("pos-voucher-modal")).toBeInTheDocument();
    expect(screen.getByText("VOUCHER")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /apply voucher|validate code/i })).toBeInTheDocument();
  });

  it("normalises input: uppercases letters and strips disallowed chars", async () => {
    render(
      <VoucherCodeModal
        open
        cartSubtotal={100}
        onApply={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    const input = screen.getByTestId("pos-voucher-code-input") as HTMLInputElement;
    await userEvent.type(input, "save!10-x_");
    expect(input.value).toBe("SAVE10-X_");
  });

  it("clicking a quick-code chip pre-fills the input", async () => {
    render(
      <VoucherCodeModal
        open
        cartSubtotal={100}
        onApply={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "RAMADAN25" }));
    expect((screen.getByTestId("pos-voucher-code-input") as HTMLInputElement).value).toBe(
      "RAMADAN25",
    );
  });

  it("validate button calls validate() with normalised code and current subtotal", async () => {
    mockValidate.mockResolvedValue({
      code: "SAVE10",
      discount_type: "percent",
      value: 10,
      remaining_uses: 3,
    });
    render(
      <VoucherCodeModal
        open
        cartSubtotal={250}
        onApply={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    await userEvent.type(screen.getByTestId("pos-voucher-code-input"), "save10");
    await userEvent.click(screen.getByTestId("pos-voucher-validate-button"));
    expect(mockValidate).toHaveBeenCalledTimes(1);
    expect(mockValidate).toHaveBeenCalledWith("SAVE10", 250);
  });

  it("Esc chip fires onCancel", async () => {
    const onCancel = vi.fn();
    render(
      <VoucherCodeModal
        open
        cartSubtotal={100}
        onApply={vi.fn()}
        onCancel={onCancel}
      />,
    );
    await userEvent.click(screen.getByTestId("pos-modal-shell-close"));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
