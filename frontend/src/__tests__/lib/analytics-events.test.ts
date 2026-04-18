import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock trackEvent so we can assert calls without touching real PostHog.
vi.mock("@/lib/analytics", () => ({
  trackEvent: vi.fn(),
}));

import { trackEvent } from "@/lib/analytics";
import {
  trackUploadStarted,
  trackUploadCompleted,
  trackFirstDashboardView,
  trackFirstInsightSeen,
  GOLDEN_PATH_EVENTS,
  __resetGoldenPathSessionGuardsForTest,
} from "@/lib/analytics-events";

const mockedTrackEvent = trackEvent as unknown as ReturnType<typeof vi.fn>;

describe("analytics-events", () => {
  beforeEach(() => {
    mockedTrackEvent.mockReset();
    sessionStorage.clear();
    __resetGoldenPathSessionGuardsForTest();
  });

  describe("GOLDEN_PATH_EVENTS constants", () => {
    it("exposes the four canonical golden-path event names", () => {
      expect(GOLDEN_PATH_EVENTS).toEqual({
        UPLOAD_STARTED: "upload_started",
        UPLOAD_COMPLETED: "upload_completed",
        FIRST_DASHBOARD_VIEW: "first_dashboard_view",
        FIRST_INSIGHT_SEEN: "first_insight_seen",
      });
    });
  });

  describe("trackUploadStarted", () => {
    it("fires upload_started event on first call in a session", () => {
      trackUploadStarted();

      expect(mockedTrackEvent).toHaveBeenCalledTimes(1);
      expect(mockedTrackEvent).toHaveBeenCalledWith(
        "upload_started",
        expect.objectContaining({ ttfi_seam: "upload_started" }),
      );
    });

    it("is idempotent within a session (fires only once)", () => {
      trackUploadStarted();
      trackUploadStarted();
      trackUploadStarted();

      expect(mockedTrackEvent).toHaveBeenCalledTimes(1);
    });

    it("fires again after session guards are reset", () => {
      trackUploadStarted();
      __resetGoldenPathSessionGuardsForTest();
      trackUploadStarted();

      expect(mockedTrackEvent).toHaveBeenCalledTimes(2);
    });
  });

  describe("trackUploadCompleted", () => {
    it("passes run_id, duration_seconds, and rows_loaded through", () => {
      trackUploadCompleted({
        run_id: "r-123",
        duration_seconds: 42.5,
        rows_loaded: 5000,
      });

      expect(mockedTrackEvent).toHaveBeenCalledWith(
        "upload_completed",
        expect.objectContaining({
          run_id: "r-123",
          duration_seconds: 42.5,
          rows_loaded: 5000,
          ttfi_seam: "upload_completed",
        }),
      );
    });

    it("is idempotent per run_id (not global)", () => {
      // Different runs should both fire.
      trackUploadCompleted({ run_id: "r-1", duration_seconds: 10, rows_loaded: 100 });
      trackUploadCompleted({ run_id: "r-2", duration_seconds: 20, rows_loaded: 200 });
      // Same run fired twice should only count once.
      trackUploadCompleted({ run_id: "r-1", duration_seconds: 10, rows_loaded: 100 });

      expect(mockedTrackEvent).toHaveBeenCalledTimes(2);
    });

    it("accepts null rows_loaded", () => {
      trackUploadCompleted({
        run_id: "r-null",
        duration_seconds: 5,
        rows_loaded: null,
      });

      expect(mockedTrackEvent).toHaveBeenCalledWith(
        "upload_completed",
        expect.objectContaining({ rows_loaded: null }),
      );
    });
  });

  describe("trackFirstDashboardView", () => {
    it("fires first_dashboard_view on first call", () => {
      trackFirstDashboardView();

      expect(mockedTrackEvent).toHaveBeenCalledWith(
        "first_dashboard_view",
        expect.objectContaining({ ttfi_seam: "first_dashboard_view" }),
      );
    });

    it("is idempotent within a session", () => {
      trackFirstDashboardView();
      trackFirstDashboardView();

      expect(mockedTrackEvent).toHaveBeenCalledTimes(1);
    });
  });

  describe("trackFirstInsightSeen", () => {
    it("fires first_insight_seen with kind and confidence props", () => {
      trackFirstInsightSeen({ kind: "expiry_risk", confidence: 0.82 });

      expect(mockedTrackEvent).toHaveBeenCalledWith(
        "first_insight_seen",
        expect.objectContaining({
          kind: "expiry_risk",
          confidence: 0.82,
          ttfi_seam: "first_insight_seen",
        }),
      );
    });

    it("is idempotent within a session", () => {
      trackFirstInsightSeen({ kind: "mom_change", confidence: 0.5 });
      trackFirstInsightSeen({ kind: "stock_risk", confidence: 0.9 });

      expect(mockedTrackEvent).toHaveBeenCalledTimes(1);
    });
  });

  describe("all four events share the same ttfi_seam property", () => {
    it("stamps every event so PostHog funnel can filter to golden-path only", () => {
      trackUploadStarted();
      trackUploadCompleted({ run_id: "r-x", duration_seconds: 1, rows_loaded: 10 });
      trackFirstDashboardView();
      trackFirstInsightSeen({ kind: "top_seller", confidence: 0.3 });

      expect(mockedTrackEvent).toHaveBeenCalledTimes(4);
      for (const call of mockedTrackEvent.mock.calls) {
        const [, props] = call;
        expect(props).toHaveProperty("ttfi_seam");
      }
    });
  });

  describe("window CustomEvent emitter", () => {
    it("dispatches a 'ttfi:event' CustomEvent on every tracked event, regardless of PostHog config", () => {
      const received: { name: string; properties: Record<string, unknown> }[] = [];
      const listener = (e: Event) => {
        const detail = (e as CustomEvent).detail;
        received.push(detail);
      };
      window.addEventListener("ttfi:event", listener);

      try {
        trackUploadStarted();
        trackUploadCompleted({ run_id: "r-1", duration_seconds: 2, rows_loaded: 50 });
        trackFirstDashboardView();
        trackFirstInsightSeen({ kind: "expiry_risk", confidence: 0.8 });

        expect(received).toHaveLength(4);
        expect(received[0].name).toBe("upload_started");
        expect(received[1].name).toBe("upload_completed");
        expect(received[1].properties).toMatchObject({
          run_id: "r-1",
          duration_seconds: 2,
          rows_loaded: 50,
        });
        expect(received[2].name).toBe("first_dashboard_view");
        expect(received[3].name).toBe("first_insight_seen");
        for (const e of received) {
          expect(e.properties).toHaveProperty("ttfi_seam", e.name);
        }
      } finally {
        window.removeEventListener("ttfi:event", listener);
      }
    });

    it("CustomEvent respects idempotency guards (no duplicate dispatch)", () => {
      let count = 0;
      const listener = () => count++;
      window.addEventListener("ttfi:event", listener);

      try {
        trackUploadStarted();
        trackUploadStarted();
        trackUploadStarted();

        expect(count).toBe(1);
      } finally {
        window.removeEventListener("ttfi:event", listener);
      }
    });
  });
});
