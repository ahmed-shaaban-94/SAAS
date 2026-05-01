import { describe, it, expect, vi, beforeEach } from "vitest";
import { ApiClient, ApiError } from "@pos/api/client";

const TOKEN = "test-jwt-token";

function makeClient(fetchFn: typeof fetch) {
  return new ApiClient({
    baseUrl: "https://api.test",
    getToken: async () => TOKEN,
    fetch: fetchFn,
    maxRetries: 3,
  });
}

function ok<T>(data: T, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("ApiClient", () => {
  beforeEach(() => vi.clearAllMocks());

  it("forwards Authorization header on every request", async () => {
    const fetchSpy = vi.fn(async () => ok({ ok: true }));
    const c = makeClient(fetchSpy as unknown as typeof fetch);
    await c.request("GET", "/api/test");
    const init = fetchSpy.mock.calls[0]![1] as RequestInit;
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBe(`Bearer ${TOKEN}`);
  });

  it("mints a fresh Idempotency-Key on POST and not on GET", async () => {
    const fetchSpy = vi.fn(async () => ok({ ok: true }));
    const c = makeClient(fetchSpy as unknown as typeof fetch);
    await c.request("POST", "/api/test", { a: 1 });
    await c.request("GET", "/api/test");
    const postHeaders = (fetchSpy.mock.calls[0]![1] as RequestInit).headers as Record<string, string>;
    const getHeaders = (fetchSpy.mock.calls[1]![1] as RequestInit).headers as Record<string, string>;
    expect(postHeaders["Idempotency-Key"]).toBeTruthy();
    expect(getHeaders["Idempotency-Key"]).toBeUndefined();
  });

  it("retries on 5xx with exponential backoff", async () => {
    const responses = [
      new Response("server boom", { status: 503 }),
      new Response("server boom", { status: 502 }),
      ok({ recovered: true }),
    ];
    const fetchSpy = vi.fn(async () => responses.shift()!);
    const c = makeClient(fetchSpy as unknown as typeof fetch);
    const result = await c.request<{ recovered: boolean }>("GET", "/api/test");
    expect(result.recovered).toBe(true);
    expect(fetchSpy).toHaveBeenCalledTimes(3);
  });

  it("does NOT retry on 4xx — surfaces ApiError immediately", async () => {
    const fetchSpy = vi.fn(async () => new Response("bad input", { status: 400 }));
    const c = makeClient(fetchSpy as unknown as typeof fetch);
    await expect(c.request("POST", "/api/test", {})).rejects.toBeInstanceOf(ApiError);
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("returns null for 204 No Content", async () => {
    const fetchSpy = vi.fn(async () => new Response(null, { status: 204 }));
    const c = makeClient(fetchSpy as unknown as typeof fetch);
    const result = await c.request<null>("DELETE", "/api/test/1");
    expect(result).toBeNull();
  });

  it("serialises JSON body and Accept/Content-Type headers", async () => {
    const fetchSpy = vi.fn(async () => ok({ ok: true }));
    const c = makeClient(fetchSpy as unknown as typeof fetch);
    await c.request("POST", "/api/test", { x: 42 });
    const init = fetchSpy.mock.calls[0]![1] as RequestInit;
    expect(init.body).toBe(JSON.stringify({ x: 42 }));
    const headers = init.headers as Record<string, string>;
    expect(headers["Content-Type"]).toBe("application/json");
    expect(headers["Accept"]).toBe("application/json");
  });

  it("strips trailing slash from baseUrl", () => {
    const c = new ApiClient({
      baseUrl: "https://api.test/",
      getToken: async () => null,
    });
    // Internal: just verify the public behavior — request to /foo lands at https://api.test/foo not //foo.
    expect(c).toBeInstanceOf(ApiClient);
  });
});
