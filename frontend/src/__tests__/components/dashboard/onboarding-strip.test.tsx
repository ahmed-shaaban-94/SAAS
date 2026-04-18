import { describe, it, expect, beforeEach, afterEach, vi, type Mock } from "vitest";
import { render, screen, act, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("@/hooks/use-onboarding", () => ({
  useOnboarding: vi.fn(),
}));

import { useOnboarding } from "@/hooks/use-onboarding";
import { OnboardingStrip } from "@/components/dashboard/onboarding-strip";

const mockedHook = useOnboarding as unknown as Mock;
const updateGoldenPathProgress = vi.fn().mockResolvedValue({});

function mockOnboarding(golden_path_progress: Record<string, string | null> = {}) {
  mockedHook.mockReturnValue({
    data: { golden_path_progress },
    updateGoldenPathProgress,
    dismissFirstInsight: vi.fn(),
  });
}

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
    updateGoldenPathProgress.mockReset().mockResolvedValue({});
    mockOnboarding();
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
    const first = render(<OnboardingStrip />);
    dispatchTtfi("upload_started");
    first.unmount();
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

  // ------------------------------------------------------------------
  // Backend sync tests (follow-up #6b)
  // ------------------------------------------------------------------

  it("syncs completed steps to backend when a step completes", async () => {
    render(<OnboardingStrip />);
    dispatchTtfi("upload_started");
    await waitFor(() => expect(updateGoldenPathProgress).toHaveBeenCalled());
    const calls = updateGoldenPathProgress.mock.calls as [Record<string, string | null>][];
    // Use the last call: earlier calls (if any) may be empty-progress guards.
    const [progress] = calls[calls.length - 1];
    expect(progress.connect_data).toMatch(/\d{4}-\d{2}-\d{2}T/);
  });

  it("merges backend golden_path_progress into local state on mount", async () => {
    const backendTs = "2026-04-18T08:00:00.000Z";
    mockOnboarding({ connect_data: backendTs });

    const { container } = render(<OnboardingStrip />);

    await waitFor(() =>
      expect(
        container.querySelector(
          '[data-step="connect_data"][data-step-state="complete"]',
        ),
      ).toBeTruthy(),
    );
  });

  it("does not overwrite locally-completed steps with null from backend", async () => {
    // Step 1 already completed locally.
    const localTs = new Date().toISOString();
    localStorage.setItem(
      STATE_KEY,
      JSON.stringify({ completed: { connect_data: localTs } }),
    );
    // Backend has connect_data as null (not yet synced).
    mockOnboarding({ connect_data: null });

    const { container } = render(<OnboardingStrip />);

    // Local value should be preserved.
    expect(
      container.querySelector(
        '[data-step="connect_data"][data-step-state="complete"]',
      ),
    ).toBeTruthy();
  });
});
