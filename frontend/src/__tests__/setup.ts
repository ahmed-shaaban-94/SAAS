import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, vi } from "vitest";
import { server } from "./mocks/server";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => "/dashboard",
  useSearchParams: () => new URLSearchParams(),
}));

// Mock react-router-dom hooks so POS page tests can render without a Router
// wrapper. Test files that need real routing wrap the render in a
// <MemoryRouter> manually; these stubs cover the unwrapped case.
vi.mock("react-router-dom", async (importActual) => {
  const actual = await importActual<typeof import("react-router-dom")>();
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useLocation: () => ({ pathname: "/", search: "", hash: "", state: null, key: "default" }),
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
    useParams: () => ({}),
  };
});

// Mock next-themes
vi.mock("next-themes", () => ({
  useTheme: () => ({ theme: "dark", setTheme: vi.fn(), resolvedTheme: "dark" }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock next-auth
vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: { user: { name: "Test User" } }, status: "authenticated" }),
  signOut: vi.fn(),
  getSession: vi.fn().mockResolvedValue({ accessToken: "test-token" }),
  SessionProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock ResizeObserver (used by Recharts)
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// MSW server lifecycle
beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  cleanup();
  server.resetHandlers();
});
afterAll(() => server.close());
