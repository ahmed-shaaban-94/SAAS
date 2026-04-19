import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent, renderHook, act } from "@testing-library/react";
import {
  HorizonProvider,
  useHorizon,
  type HorizonMode,
} from "@/components/horizon/horizon-context";
import { HorizonToggle } from "@/components/horizon/horizon-toggle";

beforeEach(() => {
  sessionStorage.clear();
});

describe("HorizonProvider + useHorizon", () => {
  it("defaults to today mode when no sessionStorage value exists", () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <HorizonProvider>{children}</HorizonProvider>
    );
    const { result } = renderHook(() => useHorizon(), { wrapper });
    expect(result.current.mode).toBe("today");
    expect(result.current.isForecast).toBe(false);
    expect(result.current.daysOut).toBe(0);
  });

  it("rehydrates from sessionStorage on mount", () => {
    sessionStorage.setItem("dp_horizon_mode_v1", "h90");
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <HorizonProvider>{children}</HorizonProvider>
    );
    const { result } = renderHook(() => useHorizon(), { wrapper });
    expect(result.current.mode).toBe("h90");
    expect(result.current.isForecast).toBe(true);
    expect(result.current.daysOut).toBe(90);
  });

  it("persists mode to sessionStorage on setMode", () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <HorizonProvider>{children}</HorizonProvider>
    );
    const { result } = renderHook(() => useHorizon(), { wrapper });
    act(() => result.current.setMode("h30"));
    expect(result.current.mode).toBe("h30");
    expect(result.current.daysOut).toBe(30);
    expect(sessionStorage.getItem("dp_horizon_mode_v1")).toBe("h30");
  });

  it("returns permissive defaults when no provider is mounted", () => {
    const { result } = renderHook(() => useHorizon());
    expect(result.current.mode).toBe("today");
    expect(result.current.isForecast).toBe(false);
  });

  it("rejects invalid stored values gracefully", () => {
    sessionStorage.setItem("dp_horizon_mode_v1", "garbage" as HorizonMode);
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <HorizonProvider>{children}</HorizonProvider>
    );
    const { result } = renderHook(() => useHorizon(), { wrapper });
    expect(result.current.mode).toBe("today");
  });
});

describe("HorizonToggle", () => {
  const setup = () =>
    render(
      <HorizonProvider>
        <HorizonToggle />
      </HorizonProvider>,
    );

  it("renders three options: Today, 30d, 90d", () => {
    setup();
    expect(screen.getByRole("button", { name: /today/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /30d/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /90d/i })).toBeInTheDocument();
  });

  it("marks the active mode with aria-pressed=true", () => {
    setup();
    const today = screen.getByRole("button", { name: /today/i });
    expect(today).toHaveAttribute("aria-pressed", "true");

    const h30 = screen.getByRole("button", { name: /30d/i });
    expect(h30).toHaveAttribute("aria-pressed", "false");
  });

  it("switches mode on click and persists to sessionStorage", () => {
    setup();
    fireEvent.click(screen.getByRole("button", { name: /30d/i }));
    expect(screen.getByRole("button", { name: /30d/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(sessionStorage.getItem("dp_horizon_mode_v1")).toBe("h30");
  });

  it("Today → 90d round-trip works", () => {
    setup();
    fireEvent.click(screen.getByRole("button", { name: /90d/i }));
    expect(screen.getByRole("button", { name: /90d/i })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: /today/i }));
    expect(screen.getByRole("button", { name: /today/i })).toHaveAttribute("aria-pressed", "true");
  });
});
