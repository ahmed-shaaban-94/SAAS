import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../../mocks/server";
import { LocaleSwitcher } from "@/components/locale-switcher";

const mockRouterRefresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: mockRouterRefresh }),
}));

describe("LocaleSwitcher", () => {
  beforeEach(() => {
    mockRouterRefresh.mockClear();
    // Add a handler for /api/locale that returns success
    server.use(
      http.post("/api/locale", () =>
        HttpResponse.json({ locale: "ar" }, { status: 200 }),
      ),
    );
  });

  it("renders both language buttons", () => {
    render(<LocaleSwitcher currentLocale="en" />);
    expect(screen.getByRole("button", { name: /english/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /arabic/i })).toBeInTheDocument();
  });

  it("highlights the current locale", () => {
    render(<LocaleSwitcher currentLocale="ar" />);
    const ar = screen.getByRole("button", { name: /arabic/i });
    expect(ar).toHaveAttribute("aria-pressed", "true");
  });

  it("clicking a different locale posts to /api/locale and refreshes the router", async () => {
    render(<LocaleSwitcher currentLocale="en" />);
    fireEvent.click(screen.getByRole("button", { name: /arabic/i }));
    await waitFor(() => expect(mockRouterRefresh).toHaveBeenCalled(), { timeout: 3000 });
  });

  it("clicking the current locale is a no-op", async () => {
    const spy = vi.fn();
    server.use(http.post("/api/locale", spy));
    render(<LocaleSwitcher currentLocale="en" />);
    fireEvent.click(screen.getByRole("button", { name: /english/i }));
    // give microtasks a chance
    await Promise.resolve();
    expect(spy).not.toHaveBeenCalled();
    expect(mockRouterRefresh).not.toHaveBeenCalled();
  });
});
