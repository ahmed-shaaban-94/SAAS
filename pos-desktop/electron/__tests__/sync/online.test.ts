import { checkOnline, isOnline, resetOnlineState } from "../../sync/online";

const BASE = "https://example.com";

afterEach(() => {
  jest.restoreAllMocks();
  resetOnlineState();
});

describe("checkOnline", () => {
  it("returns true and sets online when HEAD /health responds 200", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, status: 200 } as Response);
    const result = await checkOnline(BASE);
    expect(result).toBe(true);
    expect(isOnline()).toBe(true);
    expect(fetch).toHaveBeenCalledWith(`${BASE}/health`, expect.objectContaining({ method: "HEAD" }));
  });

  it("stays online for a single failure (degraded, not yet offline)", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, status: 200 } as Response);
    await checkOnline(BASE);  // seed online state

    global.fetch = jest.fn().mockRejectedValue(new Error("network error"));
    await checkOnline(BASE);
    expect(isOnline()).toBe(true);  // 1 failure < OFFLINE_THRESHOLD(3)
  });

  it("becomes offline after 3 consecutive failures", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, status: 200 } as Response);
    await checkOnline(BASE);

    global.fetch = jest.fn().mockRejectedValue(new Error("timeout"));
    await checkOnline(BASE);
    await checkOnline(BASE);
    await checkOnline(BASE);  // 3rd failure
    expect(isOnline()).toBe(false);
  });

  it("recovers to online after a single successful ping", async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error("down"));
    await checkOnline(BASE);
    await checkOnline(BASE);
    await checkOnline(BASE);
    expect(isOnline()).toBe(false);

    global.fetch = jest.fn().mockResolvedValue({ ok: true, status: 200 } as Response);
    await checkOnline(BASE);
    expect(isOnline()).toBe(true);
  });

  it("returns false (not ok) when server responds 503", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 503 } as Response);
    await checkOnline(BASE);
    await checkOnline(BASE);
    await checkOnline(BASE);
    const result = await checkOnline(BASE);
    expect(result).toBe(false);
  });
});
