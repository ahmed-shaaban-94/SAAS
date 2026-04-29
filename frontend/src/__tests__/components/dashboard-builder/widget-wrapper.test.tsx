import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { WidgetWrapper } from "@/components/dashboard-builder/widget-wrapper";

function Bomb(): never {
  throw new Error("widget exploded");
}

describe("WidgetWrapper error isolation", () => {
  it("renders children normally when no error", () => {
    render(
      <WidgetWrapper title="Revenue" editMode={false}>
        <div>chart content</div>
      </WidgetWrapper>,
    );
    expect(screen.getByText("chart content")).toBeTruthy();
  });

  it("shows fallback when child crashes — does not propagate", () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <WidgetWrapper title="Revenue" editMode={false}>
        <Bomb />
      </WidgetWrapper>,
    );
    expect(screen.queryByText("chart content")).toBeNull();
    expect(screen.getByRole("button", { name: /retry/i })).toBeTruthy();
    consoleError.mockRestore();
  });
});
