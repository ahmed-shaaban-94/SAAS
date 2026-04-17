import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { OnboardingStrip } from "@/components/dashboard/onboarding-strip";

const STATE_KEY = "ttfi_onboarding_strip_v1";

function dispatchTtfi(name: string) {
  act(() => {
    window.dispatchEvent(
      new CustomEvent("ttfi:event", {
        detail: { name, properties: { ttfi_seam: name } },
      }),
    );
  });
}

describe("OnboardingStrip", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.useRealTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders four step labels on first mount", () => {
    render(<OnboardingStrip />);
    expect(screen.getByText(/connect data/i)).toBeInTheDocument();
    expect(screen.getByText(/validate/i)).toBeInTheDocument();
    expect(screen.getByText(/see first insight/i)).toBeInTheDocument();
    expect(screen.getByText(/share with teammate/i)).toBeInTheDocument();
  });

  it("all steps start pending", () => {
    const { container } = render(<OnboardingStrip />);
    const complete = container.querySelectorAll('[data-step-state="complete"]');
    expect(complete.length).toBe(0);
    const pending = container.querySelectorAll('[data-step-state="pending"]');
    expect(pending.length).toBe(4);
  });

  it("completes step 1 on upload_started", () => {
    const { container } = render(<OnboardingStrip />);
    dispatchTtfi("upload_started");
    const complete = container.querySelectorAll('[data-step-state="complete"]');
    expect(complete.length).toBe(1);
  });

  it("completes step 2 on upload_completed", () => {
    const { container } = render(<OnboardingStrip />);
    dispatchTtfi("upload_completed");
    const complete = container.querySelectorAll('[data-step-state="complete"]');
    expect(complete.length).toBe(1);
    // Step 2 label text is active.
    expect(
      container.querySelector('[data-step="validate"][data-step-state="complete"]'),
    ).toBeTruthy();
  });

  it("completes step 3 on first_insight_seen", () => {
    const { container } = render(<OnboardingStrip />);
    dispatchTtfi("first_insight_seen");
    expect(
      container.querySelector(
        '[data-step="first_insight"][data-step-state="complete"]',
      ),
    ).toBeTruthy();
  });

  it("auto-marks completed steps across remounts via localStorage", () => {
    // First mount completes step 1.
    const first = render(<OnboardingStrip />);
    dispatchTtfi("upload_started");
    first.unmount();
    // Second mount should remember it.
    const { container } = render(<OnboardingStrip />);
    expect(
      container.querySelector(
        '[data-step="connect_data"][data-step-state="complete"]',
      ),
    ).toBeTruthy();
  });

  it("share-with-teammate click copies a link and completes the step", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });

    const { container } = render(<OnboardingStrip />);
    const btn = screen.getByRole("button", { name: /copy share link/i });
    await userEvent.click(btn);

    expect(writeText).toHaveBeenCalled();
    expect(
      container.querySelector(
        '[data-step="share"][data-step-state="complete"]',
      ),
    ).toBeTruthy();
  });

  it("hides itself when all 4 steps are complete", () => {
    const { container } = render(<OnboardingStrip />);
    dispatchTtfi("upload_started");
    dispatchTtfi("upload_completed");
    dispatchTtfi("first_insight_seen");
    // Simulate the share step completing via manual storage.
    act(() => {
      const raw = localStorage.getItem(STATE_KEY);
      const state = raw ? JSON.parse(raw) : {};
      state.completed = {
        ...(state.completed ?? {}),
        share: new Date().toISOString(),
      };
      localStorage.setItem(STATE_KEY, JSON.stringify(state));
      window.dispatchEvent(new Event("storage"));
    });

    // Strip should self-hide: nothing rendered.
    expect(container.firstChild).toBeNull();
  });

  it("hides itself when > 14 days have passed since first mount", () => {
    const fifteenDaysAgo = new Date();
    fifteenDaysAgo.setDate(fifteenDaysAgo.getDate() - 15);
    localStorage.setItem(
      STATE_KEY,
      JSON.stringify({
        first_seen_at: fifteenDaysAgo.toISOString(),
        completed: {},
      }),
    );
    const { container } = render(<OnboardingStrip />);
    expect(container.firstChild).toBeNull();
  });

  it("records first_seen_at timestamp on initial mount", () => {
    render(<OnboardingStrip />);
    const raw = localStorage.getItem(STATE_KEY);
    expect(raw).not.toBeNull();
    const state = JSON.parse(raw!);
    expect(state.first_seen_at).toMatch(/\d{4}-\d{2}-\d{2}T/);
  });
});
