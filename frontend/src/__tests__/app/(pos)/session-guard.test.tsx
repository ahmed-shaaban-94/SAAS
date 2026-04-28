import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

const signInMock = vi.fn();
const useSessionMock = vi.fn();
const usePathnameMock = vi.fn();

vi.mock("@/lib/auth-bridge", () => ({
  useSession: () => useSessionMock(),
  signIn: (...args: unknown[]) => signInMock(...args),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => usePathnameMock(),
}));

import { PosSessionGuard } from "@/components/auth/pos-session-guard";

describe("PosSessionGuard (audit C3 — POS desktop-mode auth gap)", () => {
  beforeEach(() => {
    signInMock.mockReset();
    useSessionMock.mockReset();
    usePathnameMock.mockReset();
    usePathnameMock.mockReturnValue("/terminal");
  });

  it("renders a loader while the session is loading and does NOT render children", () => {
    useSessionMock.mockReturnValue({ data: null, status: "loading" });
    render(
      <PosSessionGuard>
        <div data-testid="protected">secret</div>
      </PosSessionGuard>,
    );
    expect(screen.queryByTestId("protected")).not.toBeInTheDocument();
    expect(signInMock).not.toHaveBeenCalled();
  });

  it("renders children when the session is authenticated", () => {
    useSessionMock.mockReturnValue({
      data: { user: { name: "Test" } },
      status: "authenticated",
    });
    render(
      <PosSessionGuard>
        <div data-testid="protected">secret</div>
      </PosSessionGuard>,
    );
    expect(screen.getByTestId("protected")).toBeInTheDocument();
    expect(signInMock).not.toHaveBeenCalled();
  });

  it("triggers signIn() with the current pathname as callbackUrl when unauthenticated", () => {
    usePathnameMock.mockReturnValue("/terminal/checkout");
    useSessionMock.mockReturnValue({ data: null, status: "unauthenticated" });
    render(
      <PosSessionGuard>
        <div data-testid="protected">secret</div>
      </PosSessionGuard>,
    );
    expect(signInMock).toHaveBeenCalledTimes(1);
    expect(signInMock).toHaveBeenCalledWith(undefined, {
      callbackUrl: "/terminal/checkout",
    });
    // Children must NOT render — the terminal would otherwise call backend
    // APIs without an Authorization header (audit C3, incident 2026-04-24).
    expect(screen.queryByTestId("protected")).not.toBeInTheDocument();
  });

  it("falls back to /terminal when usePathname returns null (SSR edge)", () => {
    usePathnameMock.mockReturnValue(null);
    useSessionMock.mockReturnValue({ data: null, status: "unauthenticated" });
    render(
      <PosSessionGuard>
        <div data-testid="protected">secret</div>
      </PosSessionGuard>,
    );
    expect(signInMock).toHaveBeenCalledWith(undefined, {
      callbackUrl: "/terminal",
    });
  });

  it("triggers signIn on RefreshAccessTokenError using the current pathname", () => {
    usePathnameMock.mockReturnValue("/shift");
    useSessionMock.mockReturnValue({
      data: { error: "RefreshAccessTokenError" },
      status: "authenticated",
    });
    render(
      <PosSessionGuard>
        <div data-testid="protected">secret</div>
      </PosSessionGuard>,
    );
    expect(signInMock).toHaveBeenCalledWith(undefined, {
      callbackUrl: "/shift",
    });
  });
});
