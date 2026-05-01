import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ModalShell } from "@pos/components/ModalShell";

function renderShell(open: boolean, onClose = vi.fn()) {
  render(
    <ModalShell
      open={open}
      onClose={onClose}
      title="Example title"
      subtitle="Subline"
      badge="DEMO"
      accent="amber"
      testId="example-shell"
      icon={<svg data-testid="example-icon" />}
    >
      <div>body</div>
    </ModalShell>,
  );
  return { onClose };
}

describe("ModalShell", () => {
  it("renders nothing when closed", () => {
    renderShell(false);
    expect(screen.queryByTestId("example-shell")).not.toBeInTheDocument();
  });

  it("renders title, subtitle, badge, icon, and children when open", () => {
    renderShell(true);
    expect(screen.getByTestId("example-shell")).toBeInTheDocument();
    expect(screen.getByText("Example title")).toBeInTheDocument();
    expect(screen.getByText("Subline")).toBeInTheDocument();
    expect(screen.getByText("DEMO")).toBeInTheDocument();
    expect(screen.getByTestId("example-icon")).toBeInTheDocument();
    expect(screen.getByText("body")).toBeInTheDocument();
  });

  it("applies role=dialog and aria-modal=true", () => {
    renderShell(true);
    const dlg = screen.getByTestId("example-shell");
    expect(dlg).toHaveAttribute("role", "dialog");
    expect(dlg).toHaveAttribute("aria-modal", "true");
  });

  it("fires onClose from the Esc chip, the Escape key, and backdrop click", async () => {
    const { onClose } = renderShell(true);
    await userEvent.click(screen.getByTestId("pos-modal-shell-close"));
    expect(onClose).toHaveBeenCalledTimes(1);
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(2);
    await userEvent.click(screen.getByTestId("example-shell"));
    expect(onClose).toHaveBeenCalledTimes(3);
  });

  it("does not close on backdrop click when dismissOnBackdrop is false", async () => {
    const onClose = vi.fn();
    render(
      <ModalShell
        open
        onClose={onClose}
        title="x"
        icon={<svg />}
        dismissOnBackdrop={false}
        testId="no-backdrop-shell"
      >
        body
      </ModalShell>,
    );
    await userEvent.click(screen.getByTestId("no-backdrop-shell"));
    expect(onClose).not.toHaveBeenCalled();
  });

  it("clicks inside the dialog body do not bubble to the backdrop", async () => {
    const { onClose } = renderShell(true);
    await userEvent.click(screen.getByText("body"));
    expect(onClose).not.toHaveBeenCalled();
  });
});
