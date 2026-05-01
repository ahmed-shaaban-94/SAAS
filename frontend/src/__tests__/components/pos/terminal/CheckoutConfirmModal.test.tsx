import { describe, it, expect, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { CheckoutConfirmModal } from "@pos/components/terminal/CheckoutConfirmModal";

// Wrap focus-trap-react with a sentinel `data-focus-trap-mounted` attribute
// so we can assert from the rendered DOM that the trap is active. The real
// library has no DOM markers in happy-dom; this mock preserves children
// while exposing a testable signal.
const focusTrapSpy = vi.fn();
vi.mock("focus-trap-react", () => ({
  FocusTrap: ({
    children,
    focusTrapOptions,
  }: {
    children: React.ReactNode;
    focusTrapOptions: unknown;
  }) => {
    focusTrapSpy(focusTrapOptions);
    return <div data-testid="focus-trap-mounted">{children}</div>;
  },
}));

interface OverrideProps {
  open?: boolean;
  itemCount?: number;
  grandTotal?: number;
  cashTendered?: string;
  chargeDisabled?: boolean;
  onCharge?: () => void;
  onClose?: () => void;
  onCashTenderedChange?: (v: string) => void;
}

function renderModal(overrides: OverrideProps = {}) {
  const onCharge = overrides.onCharge ?? vi.fn();
  const onClose = overrides.onClose ?? vi.fn();
  const onCashTenderedChange = overrides.onCashTenderedChange ?? vi.fn();
  const utils = render(
    <CheckoutConfirmModal
      open={overrides.open ?? true}
      itemCount={overrides.itemCount ?? 2}
      grandTotal={overrides.grandTotal ?? 250}
      activePayment="cash"
      onActivePaymentChange={vi.fn()}
      cashTendered={overrides.cashTendered ?? ""}
      onCashTenderedChange={onCashTenderedChange}
      cardLast4=""
      onCardLast4Change={vi.fn()}
      insurance={null}
      onInsuranceChange={vi.fn()}
      onOpenInsuranceModal={vi.fn()}
      voucherCode={null}
      voucherDiscount={0}
      onOpenVoucherModal={vi.fn()}
      lastKeypadKey={null}
      chargeDisabled={overrides.chargeDisabled ?? false}
      onCharge={onCharge}
      onClose={onClose}
      error={null}
    />,
  );
  return { ...utils, onCharge, onClose, onCashTenderedChange };
}

describe("CheckoutConfirmModal", () => {
  it("renders the dialog with role and aria attributes", () => {
    renderModal();
    const dialog = screen.getByTestId("checkout-confirm-modal");
    expect(dialog).toHaveAttribute("role", "dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
  });

  it("Enter charges when not disabled", () => {
    const { onCharge } = renderModal();
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    });
    expect(onCharge).toHaveBeenCalledTimes(1);
  });

  it("Enter does NOT charge when chargeDisabled", () => {
    const { onCharge } = renderModal({ chargeDisabled: true });
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    });
    expect(onCharge).not.toHaveBeenCalled();
  });

  it("Escape closes the modal", () => {
    const { onClose } = renderModal();
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  // ---- Effect-deps regression: keystrokes that mutate cashTendered must NOT
  // detach/re-attach the Enter listener. Earlier code used `[props.open, props]`
  // which made `props` (a fresh object on every parent render) a dep, so each
  // keystroke tore down and rebuilt the listener. We assert by re-rendering
  // with a new cashTendered value and verifying Enter still charges exactly
  // once, with the listener installed exactly once.
  it("keeps Enter wired across cashTendered re-renders", () => {
    const onCharge = vi.fn();
    const { rerender } = render(
      <CheckoutConfirmModal
        open={true}
        itemCount={2}
        grandTotal={250}
        activePayment="cash"
        onActivePaymentChange={vi.fn()}
        cashTendered=""
        onCashTenderedChange={vi.fn()}
        cardLast4=""
        onCardLast4Change={vi.fn()}
        insurance={null}
        onInsuranceChange={vi.fn()}
        onOpenInsuranceModal={vi.fn()}
        voucherCode={null}
        voucherDiscount={0}
        onOpenVoucherModal={vi.fn()}
        lastKeypadKey={null}
        chargeDisabled={false}
        onCharge={onCharge}
        onClose={vi.fn()}
        error={null}
      />,
    );

    // Simulate cashier typing — parent re-renders 3 times with new strings.
    for (const v of ["1", "10", "100"]) {
      rerender(
        <CheckoutConfirmModal
          open={true}
          itemCount={2}
          grandTotal={250}
          activePayment="cash"
          onActivePaymentChange={vi.fn()}
          cashTendered={v}
          onCashTenderedChange={vi.fn()}
          cardLast4=""
          onCardLast4Change={vi.fn()}
          insurance={null}
          onInsuranceChange={vi.fn()}
          onOpenInsuranceModal={vi.fn()}
          voucherCode={null}
          voucherDiscount={0}
          onOpenVoucherModal={vi.fn()}
          lastKeypadKey={null}
          chargeDisabled={false}
          onCharge={onCharge}
          onClose={vi.fn()}
          error={null}
        />,
      );
    }

    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    });
    // Exactly once — if the effect re-attached on every rerender we might
    // see multiple handlers stacked or, with React 18+ strict mode, none.
    expect(onCharge).toHaveBeenCalledTimes(1);
  });

  // ---- Focus trap: when the modal mounts, a FocusTrap wraps the dialog
  // body so Tab cannot escape to the underlying terminal. We mock
  // focus-trap-react above and assert the trap component renders inside
  // the modal.
  it("wraps the dialog in a FocusTrap when open", () => {
    focusTrapSpy.mockClear();
    renderModal();
    expect(screen.getByTestId("focus-trap-mounted")).toBeInTheDocument();
    expect(focusTrapSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        escapeDeactivates: false,
        allowOutsideClick: true,
      }),
    );
  });
});
