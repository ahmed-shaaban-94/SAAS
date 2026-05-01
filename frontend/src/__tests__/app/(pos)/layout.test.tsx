/**
 * Audit C3 (2026-04-26): the POS layout's SessionGuard fell through to
 * children when ``status === "unauthenticated"`` in POS desktop mode
 * (where ``middleware.ts`` is short-circuited via ``POS_DESKTOP_MODE=1``).
 * That left the terminal UI reachable without a Clerk session — every
 * authed POST then 401-banner'd at the user instead of redirecting them
 * to sign in.
 *
 * These tests exercise the new behaviour: in Electron (the production
 * POS desktop runtime), unauthenticated users are pushed to ``signIn``
 * with a ``/terminal`` callback. In the SaaS web build, the guard
 * still falls through so middleware owns the redirect.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render } from "@testing-library/react";

const useSessionMock = vi.fn();
const signInMock = vi.fn();
let authProvider: "auth0" | "clerk" = "clerk";
let clerkKeyConfigured = true;

vi.mock("@/lib/auth-bridge", () => ({
  get AUTH_PROVIDER() {
    return authProvider;
  },
  get CLERK_KEY_CONFIGURED() {
    return clerkKeyConfigured;
  },
  useSession: () => useSessionMock(),
  signIn: (...args: unknown[]) => signInMock(...args),
}));

// next/font + theme + SWR providers pull in heavy modules at import time;
// the layout's auth gate is what we're testing, so mock the rest minimal.
vi.mock("next/font/google", () => ({
  Fraunces: () => ({ variable: "" }),
  JetBrains_Mono: () => ({ variable: "" }),
  Cairo: () => ({ variable: "" }),
}));
vi.mock("next-themes", () => ({
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
}));
vi.mock("swr", () => ({
  SWRConfig: ({ children }: { children: React.ReactNode }) => children,
}));
vi.mock("@/lib/swr-config", () => ({ swrConfig: {} }));
vi.mock("@/components/auth-provider", () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}));
vi.mock("@/components/error-boundary", () => ({
  ErrorBoundary: ({ children }: { children: React.ReactNode }) => children,
}));
vi.mock("@/components/ui/toast", () => ({
  ToastProvider: ({ children }: { children: React.ReactNode }) => children,
}));
vi.mock("@/components/branding/brand-provider", () => ({
  BrandProvider: ({ children }: { children: React.ReactNode }) => children,
}));
vi.mock("@/hooks/use-renderer-crash-bridge", () => ({
  useRendererCrashBridge: vi.fn(),
}));

import PosLayout from "@pos/pages/layout";

describe("PosLayout / SessionGuard — audit C3", () => {
  const originalElectronAPI = (window as unknown as { electronAPI?: unknown }).electronAPI;

  beforeEach(() => {
    authProvider = "clerk";
    clerkKeyConfigured = true;
    useSessionMock.mockReset();
    signInMock.mockReset();
  });

  afterEach(() => {
    if (originalElectronAPI === undefined) {
      delete (window as unknown as { electronAPI?: unknown }).electronAPI;
    } else {
      (window as unknown as { electronAPI?: unknown }).electronAPI = originalElectronAPI;
    }
  });

  it("redirects unauthenticated users to signIn when running in the Electron POS shell", async () => {
    (window as unknown as { electronAPI?: unknown }).electronAPI = { ping: () => "pong" };
    useSessionMock.mockReturnValue({ data: null, status: "unauthenticated" });

    render(<PosLayout>terminal-content</PosLayout>);

    // The redirect happens inside a useEffect — wait a microtask cycle.
    await Promise.resolve();

    expect(signInMock).toHaveBeenCalledTimes(1);
    expect(signInMock).toHaveBeenCalledWith(undefined, { callbackUrl: "/terminal" });
  });

  it("does NOT redirect on the SaaS web build (middleware owns auth)", async () => {
    delete (window as unknown as { electronAPI?: unknown }).electronAPI;
    useSessionMock.mockReturnValue({ data: null, status: "unauthenticated" });

    render(<PosLayout>terminal-content</PosLayout>);
    await Promise.resolve();

    expect(signInMock).not.toHaveBeenCalled();
  });

  it("does NOT redirect when the user is already authenticated", async () => {
    (window as unknown as { electronAPI?: unknown }).electronAPI = { ping: () => "pong" };
    useSessionMock.mockReturnValue({
      data: { user: { name: "Pharmacist" } },
      status: "authenticated",
    });

    render(<PosLayout>terminal-content</PosLayout>);
    await Promise.resolve();

    expect(signInMock).not.toHaveBeenCalled();
  });

  it("shows a build-config error when Clerk is missing from the build", async () => {
    clerkKeyConfigured = false;
    (window as unknown as { electronAPI?: unknown }).electronAPI = { ping: () => "pong" };
    useSessionMock.mockReturnValue({ data: null, status: "unauthenticated" });

    const { getByText } = render(<PosLayout>terminal-content</PosLayout>);
    await Promise.resolve();

    expect(getByText("Authentication not configured")).toBeTruthy();
    expect(signInMock).not.toHaveBeenCalled();
  });

  it("does not show the Clerk build-config error for Auth0 builds", async () => {
    authProvider = "auth0";
    clerkKeyConfigured = false;
    useSessionMock.mockReturnValue({
      data: { user: { name: "Pharmacist" } },
      status: "authenticated",
    });

    const { getByText, queryByText } = render(<PosLayout>terminal-content</PosLayout>);
    await Promise.resolve();

    expect(queryByText("Authentication not configured")).toBeNull();
    expect(getByText("terminal-content")).toBeTruthy();
  });
});
