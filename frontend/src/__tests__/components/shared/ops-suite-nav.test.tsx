import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn().mockReturnValue("/inventory"),
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

import { usePathname } from "next/navigation";
import { OpsSuiteNav } from "@/components/shared/ops-suite-nav";

const mockedPathname = usePathname as unknown as ReturnType<typeof vi.fn>;

describe("OpsSuiteNav", () => {
  it("renders all five ops tabs", () => {
    render(<OpsSuiteNav />);
    expect(screen.getByRole("link", { name: /inventory/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /dispensing/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /expiry/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /purchase orders/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /suppliers/i })).toBeInTheDocument();
  });

  it("marks the active tab with aria-current=page", () => {
    mockedPathname.mockReturnValue("/inventory");
    render(<OpsSuiteNav />);
    expect(screen.getByRole("link", { name: /inventory/i })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: /dispensing/i })).not.toHaveAttribute("aria-current");
  });

  it("marks /expiry as active when pathname is /expiry", () => {
    mockedPathname.mockReturnValue("/expiry");
    render(<OpsSuiteNav />);
    expect(screen.getByRole("link", { name: /expiry/i })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: /inventory/i })).not.toHaveAttribute("aria-current");
  });

  it("marks /purchase-orders as active", () => {
    mockedPathname.mockReturnValue("/purchase-orders");
    render(<OpsSuiteNav />);
    expect(screen.getByRole("link", { name: /purchase orders/i })).toHaveAttribute("aria-current", "page");
  });

  it("each tab link points to the correct href", () => {
    mockedPathname.mockReturnValue("/suppliers");
    render(<OpsSuiteNav />);
    expect(screen.getByRole("link", { name: /inventory/i })).toHaveAttribute("href", "/inventory");
    expect(screen.getByRole("link", { name: /dispensing/i })).toHaveAttribute("href", "/dispensing");
    expect(screen.getByRole("link", { name: /expiry/i })).toHaveAttribute("href", "/expiry");
    expect(screen.getByRole("link", { name: /purchase orders/i })).toHaveAttribute("href", "/purchase-orders");
    expect(screen.getByRole("link", { name: /suppliers/i })).toHaveAttribute("href", "/suppliers");
  });
});
