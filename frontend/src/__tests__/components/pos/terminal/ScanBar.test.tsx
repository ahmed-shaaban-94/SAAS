import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ScanBar } from "@pos/components/terminal/ScanBar";

describe("ScanBar", () => {
  it("calls onSubmit with the current value on form submit", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(
      <ScanBar
        value="ABC123"
        onChange={vi.fn()}
        onSubmit={onSubmit}
        isOnline
      />,
    );
    await user.type(screen.getByRole("textbox"), "{Enter}");
    expect(onSubmit).toHaveBeenCalledWith("ABC123");
  });

  describe("flash overlays (F7 + scan-flash)", () => {
    it("does not render the success flash when flashKey is undefined", () => {
      render(
        <ScanBar value="" onChange={vi.fn()} onSubmit={vi.fn()} isOnline />,
      );
      expect(screen.queryByTestId("scan-flash")).not.toBeInTheDocument();
    });

    it("does not render the success flash when flashKey is 0", () => {
      render(
        <ScanBar
          value=""
          onChange={vi.fn()}
          onSubmit={vi.fn()}
          isOnline
          flashKey={0}
        />,
      );
      expect(screen.queryByTestId("scan-flash")).not.toBeInTheDocument();
    });

    it("renders the success flash when flashKey > 0", () => {
      render(
        <ScanBar
          value=""
          onChange={vi.fn()}
          onSubmit={vi.fn()}
          isOnline
          flashKey={1}
        />,
      );
      expect(screen.getByTestId("scan-flash")).toBeInTheDocument();
      expect(screen.queryByTestId("scan-flash-error")).not.toBeInTheDocument();
    });

    it("renders the error flash when errorFlashKey > 0", () => {
      render(
        <ScanBar
          value=""
          onChange={vi.fn()}
          onSubmit={vi.fn()}
          isOnline
          errorFlashKey={3}
        />,
      );
      expect(screen.getByTestId("scan-flash-error")).toBeInTheDocument();
      expect(screen.queryByTestId("scan-flash")).not.toBeInTheDocument();
    });

    it("renders both flashes simultaneously when both keys > 0", () => {
      render(
        <ScanBar
          value=""
          onChange={vi.fn()}
          onSubmit={vi.fn()}
          isOnline
          flashKey={2}
          errorFlashKey={1}
        />,
      );
      expect(screen.getByTestId("scan-flash")).toBeInTheDocument();
      expect(screen.getByTestId("scan-flash-error")).toBeInTheDocument();
    });
  });
});
