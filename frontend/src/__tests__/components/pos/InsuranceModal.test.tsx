import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import {
  InsuranceModal,
  type InsuranceApplyPayload,
} from "@/components/pos/InsuranceModal";

const baseProps = {
  grandTotal: 200,
};

describe("InsuranceModal", () => {
  beforeEach(() => {
    // user-event types into the focused input; the modal focuses national-id
    // on open via setTimeout, so the first keystroke lands correctly.
  });

  it("renders nothing when closed", () => {
    render(
      <InsuranceModal
        open={false}
        onClose={vi.fn()}
        onApply={vi.fn()}
        {...baseProps}
      />,
    );
    expect(screen.queryByTestId("pos-insurance-modal")).not.toBeInTheDocument();
  });

  it("renders insurer grid, fields, slider, and portions when open", () => {
    render(
      <InsuranceModal open onClose={vi.fn()} onApply={vi.fn()} {...baseProps} />,
    );
    expect(screen.getByTestId("pos-insurance-modal")).toBeInTheDocument();
    expect(screen.getByTestId("pos-insurance-insurer-grid")).toBeInTheDocument();
    expect(screen.getByTestId("pos-insurance-national-id")).toBeInTheDocument();
    expect(screen.getByTestId("pos-insurance-coverage-slider")).toBeInTheDocument();
    // Default: first insurer (Med-Net, 80%)
    expect(screen.getByTestId("pos-insurance-coverage-value")).toHaveTextContent("80%");
    // Insurer pays = 200 * 0.80 = 160.00
    expect(screen.getByTestId("pos-insurance-insurer-pays")).toHaveTextContent(
      /160\.00/,
    );
    // Patient pays = 40.00
    expect(screen.getByTestId("pos-insurance-patient-pays")).toHaveTextContent(
      /40\.00/,
    );
  });

  it("switching insurer updates coverage and split", async () => {
    render(
      <InsuranceModal open onClose={vi.fn()} onApply={vi.fn()} {...baseProps} />,
    );
    await userEvent.click(screen.getByTestId("pos-insurance-insurer-bupa"));
    // Bupa default = 90%
    expect(screen.getByTestId("pos-insurance-coverage-value")).toHaveTextContent("90%");
    expect(screen.getByTestId("pos-insurance-insurer-pays")).toHaveTextContent(
      /180\.00/,
    );
    expect(screen.getByTestId("pos-insurance-patient-pays")).toHaveTextContent(
      /20\.00/,
    );
  });

  it("national id is sanitised to digits and capped at 14 chars", async () => {
    render(
      <InsuranceModal open onClose={vi.fn()} onApply={vi.fn()} {...baseProps} />,
    );
    const id = screen.getByTestId("pos-insurance-national-id") as HTMLInputElement;
    // Typed mix of letters + digits + whitespace; sanitiser must strip
    // non-digits and clamp the tail to 14.
    await userEvent.type(id, "29901011abc234567xx89");
    expect(id.value).toBe("29901011234567");
  });

  it("apply button is disabled until national id has 14 digits", async () => {
    const onApply = vi.fn();
    render(
      <InsuranceModal open onClose={vi.fn()} onApply={onApply} {...baseProps} />,
    );
    const apply = screen.getByTestId("pos-insurance-apply") as HTMLButtonElement;
    expect(apply).toBeDisabled();

    await userEvent.type(screen.getByTestId("pos-insurance-national-id"), "12345678901234");
    expect(apply).not.toBeDisabled();
  });

  it("confirm fires onApply with insurer state + pre-auth, then closes", async () => {
    const onApply = vi.fn<(p: InsuranceApplyPayload) => void>();
    const onClose = vi.fn();
    render(
      <InsuranceModal open onClose={onClose} onApply={onApply} {...baseProps} />,
    );
    await userEvent.type(screen.getByTestId("pos-insurance-national-id"), "12345678901234");
    await userEvent.type(screen.getByTestId("pos-insurance-preauth"), "PA-4422");
    await userEvent.click(screen.getByTestId("pos-insurance-apply"));

    expect(onApply).toHaveBeenCalledTimes(1);
    const payload = onApply.mock.calls[0][0];
    expect(payload.state.name).toBe("Med-Net");
    expect(payload.state.coveragePct).toBe(80);
    expect(payload.state.nationalId).toBe("12345678901234");
    expect(payload.insuranceNumber).toBe("PA-4422");
    expect(payload.insurerId).toBe("mednet");
    expect(onClose).toHaveBeenCalled();
  });

  it("returns insuranceNumber=null when pre-auth is blank", async () => {
    const onApply = vi.fn<(p: InsuranceApplyPayload) => void>();
    render(
      <InsuranceModal open onClose={vi.fn()} onApply={onApply} {...baseProps} />,
    );
    await userEvent.type(screen.getByTestId("pos-insurance-national-id"), "99999999999999");
    await userEvent.click(screen.getByTestId("pos-insurance-apply"));
    expect(onApply.mock.calls[0][0].insuranceNumber).toBeNull();
  });

  it("pre-fills insurer and nationalId when `initial` is supplied", () => {
    render(
      <InsuranceModal
        open
        onClose={vi.fn()}
        onApply={vi.fn()}
        grandTotal={100}
        initial={{ name: "Axa Egypt", coveragePct: 55, nationalId: "22222222222222" }}
      />,
    );
    // Axa default coverage is 70% but `initial.coveragePct` wins
    expect(screen.getByTestId("pos-insurance-coverage-value")).toHaveTextContent("55%");
    const id = screen.getByTestId("pos-insurance-national-id") as HTMLInputElement;
    expect(id.value).toBe("22222222222222");
  });
});
