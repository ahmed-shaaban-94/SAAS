import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";

import { TopBar } from "@/components/pos/shell/TopBar";
import messages from "../../../../../messages/en.json";

function renderTopBar(overrides: Partial<React.ComponentProps<typeof TopBar>> = {}) {
  const onSwitchScreen = vi.fn();
  const props: React.ComponentProps<typeof TopBar> = {
    screen: "terminal",
    online: true,
    queueDepth: 0,
    cashierName: "Leila",
    onSwitchScreen,
    ...overrides,
  };
  const utils = render(
    <NextIntlClientProvider locale="en" messages={messages}>
      <TopBar {...props} />
    </NextIntlClientProvider>,
  );
  return { ...utils, onSwitchScreen, props };
}

describe("TopBar", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval", "Date"] });
    vi.setSystemTime(new Date("2026-04-19T12:34:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders all four tabs with their F-key labels", () => {
    renderTopBar();
    const nav = screen.getByRole("navigation", { name: /pos primary navigation/i });
    const buttons = within(nav).getAllByRole("button");
    expect(buttons).toHaveLength(4);

    expect(within(nav).getByRole("button", { name: /terminal \(F1\)/i })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: /sync \(F2\)/i })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: /shift \(F3\)/i })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: /drugs \(F4\)/i })).toBeInTheDocument();
  });

  it("marks only the active tab with aria-current=page", () => {
    renderTopBar({ screen: "drugs" });
    const drugs = screen.getByRole("button", { name: /drugs \(F4\)/i });
    expect(drugs).toHaveAttribute("aria-current", "page");

    const terminal = screen.getByRole("button", { name: /terminal \(F1\)/i });
    expect(terminal).not.toHaveAttribute("aria-current");
  });

  it("calls onSwitchScreen with the tab id when a tab is clicked", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { onSwitchScreen } = renderTopBar();

    await user.click(screen.getByRole("button", { name: /sync \(F2\)/i }));
    expect(onSwitchScreen).toHaveBeenCalledWith("sync");

    await user.click(screen.getByRole("button", { name: /shift \(F3\)/i }));
    expect(onSwitchScreen).toHaveBeenCalledWith("shift");
  });

  it("shows green Online pill when connection is healthy", () => {
    renderTopBar({ online: true, queueDepth: 0 });
    expect(screen.getByText(/^online$/i)).toBeInTheDocument();
  });

  it("shows 'Provisional — N queued' when offline with pending queue", () => {
    renderTopBar({ online: false, queueDepth: 3 });
    expect(screen.getByText(/provisional\s*—\s*3 queued/i)).toBeInTheDocument();
  });

  it("renders the cashier name", () => {
    renderTopBar({ cashierName: "Marwa" });
    expect(screen.getByText("Marwa")).toBeInTheDocument();
  });
});
