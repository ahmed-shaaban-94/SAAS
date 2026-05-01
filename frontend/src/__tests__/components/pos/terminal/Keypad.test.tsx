import { describe, it, expect, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { Keypad } from "@pos/components/terminal/Keypad";

function KeypadHarness({ initial = "", disabled = false }: { initial?: string; disabled?: boolean }) {
  const [v, setV] = useState(initial);
  return <Keypad value={v} onChange={setV} disabled={disabled} />;
}

describe("Keypad", () => {
  it("displays the current value and a placeholder when empty", () => {
    render(<KeypadHarness />);
    expect(screen.getByTestId("keypad-value").textContent).toBe("—");
  });

  it("appends digits when number keys are pressed", async () => {
    const user = userEvent.setup();
    render(<KeypadHarness />);

    await user.click(screen.getByLabelText("key 1"));
    await user.click(screen.getByLabelText("key 2"));
    await user.click(screen.getByLabelText("key 5"));

    expect(screen.getByTestId("keypad-value").textContent).toBe("125");
  });

  it("appends a decimal point once but ignores subsequent dots", async () => {
    const user = userEvent.setup();
    render(<KeypadHarness />);

    await user.click(screen.getByLabelText("key 1"));
    await user.click(screen.getByLabelText("key ."));
    await user.click(screen.getByLabelText("key 5"));
    await user.click(screen.getByLabelText("key ."));
    await user.click(screen.getByLabelText("key 0"));

    expect(screen.getByTestId("keypad-value").textContent).toBe("1.50");
  });

  it("pops the last char when backspace is pressed", async () => {
    const user = userEvent.setup();
    render(<KeypadHarness initial="123" />);

    await user.click(screen.getByLabelText("backspace"));

    expect(screen.getByTestId("keypad-value").textContent).toBe("12");
  });

  it("disables all keys when disabled=true", async () => {
    const user = userEvent.setup();
    render(<KeypadHarness disabled />);
    const key = screen.getByLabelText("key 1");
    expect(key).toBeDisabled();
    await user.click(key);
    // Still empty
    expect(screen.getByTestId("keypad-value").textContent).toBe("—");
  });

  it("renders a ghost indicator when lastKey prop changes", () => {
    vi.useFakeTimers();
    const { rerender } = render(
      <Keypad value="" onChange={vi.fn()} lastKey="7" />,
    );

    expect(screen.getByTestId("keypad-ghost")).toHaveTextContent("7");

    // Advance past fade-out
    act(() => {
      vi.advanceTimersByTime(400);
    });
    rerender(<Keypad value="" onChange={vi.fn()} lastKey="7" />);

    expect(screen.queryByTestId("keypad-ghost")).not.toBeInTheDocument();

    vi.useRealTimers();
  });
});
