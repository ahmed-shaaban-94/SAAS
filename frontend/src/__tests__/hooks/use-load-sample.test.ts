import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

vi.mock("@/lib/api-client", () => ({
  postAPI: vi.fn(),
}));

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, refresh: vi.fn() }),
}));

const trackUploadCompletedMock = vi.fn();
vi.mock("@/lib/analytics-events", () => ({
  trackUploadCompleted: (...args: unknown[]) => trackUploadCompletedMock(...args),
}));

import { postAPI } from "@/lib/api-client";
import { useLoadSample } from "@/hooks/use-load-sample";

const mockedPost = postAPI as unknown as Mock;

describe("useLoadSample", () => {
  beforeEach(() => {
    mockedPost.mockReset();
    pushMock.mockReset();
    trackUploadCompletedMock.mockReset();
  });

  it("exposes loading=false and error=null initially", () => {
    const { result } = renderHook(() => useLoadSample());
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(typeof result.current.loadSample).toBe("function");
  });

  it("loadSample calls /api/v1/onboarding/load-sample and redirects by default", async () => {
    mockedPost.mockResolvedValue({
      rows_loaded: 5000,
      pipeline_run_id: "run-1",
      duration_seconds: 4.2,
    });

    const { result } = renderHook(() => useLoadSample());

    await act(async () => {
      await result.current.loadSample();
    });

    expect(mockedPost).toHaveBeenCalledWith("/api/v1/onboarding/load-sample");
    expect(pushMock).toHaveBeenCalledWith("/dashboard?first_upload=1");
  });

  it("fires trackUploadCompleted with the returned metadata", async () => {
    mockedPost.mockResolvedValue({
      rows_loaded: 5000,
      pipeline_run_id: "run-xyz",
      duration_seconds: 4.2,
    });

    const { result } = renderHook(() => useLoadSample());

    await act(async () => {
      await result.current.loadSample();
    });

    expect(trackUploadCompletedMock).toHaveBeenCalledWith({
      run_id: "run-xyz",
      duration_seconds: 4.2,
      rows_loaded: 5000,
    });
  });

  it("sets loading=true while the request is in flight", async () => {
    let resolveFn: (v: unknown) => void = () => {};
    mockedPost.mockReturnValue(new Promise((r) => (resolveFn = r)));

    const { result } = renderHook(() => useLoadSample());

    act(() => {
      void result.current.loadSample();
    });

    await waitFor(() => expect(result.current.loading).toBe(true));

    act(() => {
      resolveFn({
        rows_loaded: 1,
        pipeline_run_id: "r",
        duration_seconds: 1,
      });
    });

    await waitFor(() => expect(result.current.loading).toBe(false));
  });

  it("on failure: sets error, does not redirect, does not track", async () => {
    mockedPost.mockRejectedValue(new Error("boom"));

    const { result } = renderHook(() => useLoadSample());

    await act(async () => {
      await result.current.loadSample();
    });

    expect(result.current.error).toMatch(/could not load sample data/i);
    expect(pushMock).not.toHaveBeenCalled();
    expect(trackUploadCompletedMock).not.toHaveBeenCalled();
    expect(result.current.loading).toBe(false);
  });

  it("accepts a redirect override", async () => {
    mockedPost.mockResolvedValue({
      rows_loaded: 5000,
      pipeline_run_id: "r",
      duration_seconds: 1,
    });

    const { result } = renderHook(() =>
      useLoadSample({ redirectTo: "/insights?first=1" }),
    );

    await act(async () => {
      await result.current.loadSample();
    });

    expect(pushMock).toHaveBeenCalledWith("/insights?first=1");
  });

  it("redirectTo: null disables redirect entirely", async () => {
    mockedPost.mockResolvedValue({
      rows_loaded: 5000,
      pipeline_run_id: "r",
      duration_seconds: 1,
    });

    const { result } = renderHook(() => useLoadSample({ redirectTo: null }));

    await act(async () => {
      await result.current.loadSample();
    });

    expect(pushMock).not.toHaveBeenCalled();
    // Tracker should still fire — it's independent of redirect.
    expect(trackUploadCompletedMock).toHaveBeenCalled();
  });

  it("clears previous error on a subsequent attempt", async () => {
    mockedPost.mockRejectedValueOnce(new Error("first boom"));
    mockedPost.mockResolvedValueOnce({
      rows_loaded: 5000,
      pipeline_run_id: "r",
      duration_seconds: 1,
    });

    const { result } = renderHook(() => useLoadSample());

    await act(async () => {
      await result.current.loadSample();
    });
    expect(result.current.error).not.toBeNull();

    await act(async () => {
      await result.current.loadSample();
    });
    expect(result.current.error).toBeNull();
  });
});
