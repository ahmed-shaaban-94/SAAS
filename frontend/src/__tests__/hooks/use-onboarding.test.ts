import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

vi.mock("swr", () => ({
  default: vi.fn(),
}));

vi.mock("@/lib/api-client", () => ({
  fetchAPI: vi.fn(),
  postAPI: vi.fn(),
  putAPI: vi.fn(),
  swrKey: (k: string) => k,
}));

import useSWR from "swr";
import { postAPI, putAPI } from "@/lib/api-client";
import { useOnboarding } from "@/hooks/use-onboarding";

const mockedSWR = useSWR as unknown as Mock;
const mockedPost = postAPI as unknown as Mock;
const mockedPut = putAPI as unknown as Mock;

const baseStatus = {
  steps_completed: [],
  current_step: "connect_data",
  is_complete: false,
  skipped_at: null,
  completed_at: null,
  golden_path_progress: {},
  first_insight_dismissed_at: null,
};

describe("useOnboarding — updateGoldenPathProgress", () => {
  beforeEach(() => {
    mockedSWR.mockReturnValue({
      data: baseStatus,
      error: null,
      isLoading: false,
      mutate: vi.fn(),
    });
    mockedPut.mockReset();
    mockedPost.mockReset();
  });

  it("calls putAPI with /api/v1/onboarding/golden-path-progress", async () => {
    const progress = { upload_data: "2026-04-18T10:00:00Z", validate: null };
    mockedPut.mockResolvedValue({ ...baseStatus, golden_path_progress: progress });

    const { result } = renderHook(() => useOnboarding());

    await act(async () => {
      await result.current.updateGoldenPathProgress(progress);
    });

    expect(mockedPut).toHaveBeenCalledWith(
      "/api/v1/onboarding/golden-path-progress",
      { progress },
    );
  });

  it("updates SWR cache after successful put", async () => {
    const mutate = vi.fn();
    mockedSWR.mockReturnValue({
      data: baseStatus,
      error: null,
      isLoading: false,
      mutate,
    });
    const progress = { upload_data: "2026-04-18T10:00:00Z" };
    const updated = { ...baseStatus, golden_path_progress: progress };
    mockedPut.mockResolvedValue(updated);

    const { result } = renderHook(() => useOnboarding());

    await act(async () => {
      await result.current.updateGoldenPathProgress(progress);
    });

    expect(mutate).toHaveBeenCalledWith(updated, false);
  });
});

describe("useOnboarding — dismissFirstInsight", () => {
  beforeEach(() => {
    mockedSWR.mockReturnValue({
      data: baseStatus,
      error: null,
      isLoading: false,
      mutate: vi.fn(),
    });
    mockedPost.mockReset();
    mockedPut.mockReset();
  });

  it("calls postAPI with /api/v1/onboarding/dismiss-first-insight", async () => {
    const dismissed = { ...baseStatus, first_insight_dismissed_at: "2026-04-18T10:00:00Z" };
    mockedPost.mockResolvedValue(dismissed);

    const { result } = renderHook(() => useOnboarding());

    await act(async () => {
      await result.current.dismissFirstInsight();
    });

    expect(mockedPost).toHaveBeenCalledWith(
      "/api/v1/onboarding/dismiss-first-insight",
    );
  });

  it("updates SWR cache after successful dismiss", async () => {
    const mutate = vi.fn();
    mockedSWR.mockReturnValue({
      data: baseStatus,
      error: null,
      isLoading: false,
      mutate,
    });
    const dismissed = { ...baseStatus, first_insight_dismissed_at: "2026-04-18T10:00:00Z" };
    mockedPost.mockResolvedValue(dismissed);

    const { result } = renderHook(() => useOnboarding());

    await act(async () => {
      await result.current.dismissFirstInsight();
    });

    expect(mutate).toHaveBeenCalledWith(dismissed, false);
  });
});
