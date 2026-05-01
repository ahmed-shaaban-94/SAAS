// Typed POS API client. Wraps fetch with auth + Idempotency-Key + retry.
// Generated types: src/api/types.ts (via `openapi-typescript`).
// Per-resource endpoint wrappers: src/api/endpoints/*.ts.
//
// Phase 1 Sub-PR 4 of POS extraction. Replaces ad-hoc fetchAPI/postAPI/
// patchAPI calls used across POS code.

import type { paths } from "@pos/api/types";

type Method = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

export interface ApiClientOptions {
  /** Base URL for the API (e.g. "https://smartdatapulse.tech"). No trailing slash. */
  baseUrl: string;
  /** Returns the current bearer token (Clerk JWT) or null when unauthenticated. */
  getToken: () => Promise<string | null>;
  /** Override fetch (test injection / retry instrumentation). Defaults to global fetch. */
  fetch?: typeof fetch;
  /** Number of retry attempts on transient (5xx) errors. Default: 3. */
  maxRetries?: number;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly body?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Thin typed wrapper around fetch. Endpoint modules under
 * `pos-desktop/src/api/endpoints/` consume this for typed calls.
 *
 * Behavior:
 * - Auth header forwarded via `Authorization: Bearer <token>` when getToken
 *   returns non-null.
 * - POST requests get a fresh `Idempotency-Key: <uuid>` header to align with
 *   the backend's idempotency middleware. PATCH/PUT/DELETE do not — those
 *   verbs already carry the resource id which the backend uses for replay
 *   detection.
 * - Retries on 5xx with exponential backoff (250ms × 2^attempt). Does not
 *   retry on 4xx (those are deterministic — retrying would just re-fail).
 * - Network errors (no response) get 1 retry then surface as ApiError(0).
 * - JSON request bodies are stringified; JSON responses are parsed.
 */
export class ApiClient {
  private readonly baseUrl: string;
  private readonly getToken: () => Promise<string | null>;
  private readonly fetchFn: typeof fetch;
  private readonly maxRetries: number;

  constructor(opts: ApiClientOptions) {
    this.baseUrl = opts.baseUrl.replace(/\/+$/, "");
    this.getToken = opts.getToken;
    this.fetchFn = opts.fetch ?? globalThis.fetch.bind(globalThis);
    this.maxRetries = opts.maxRetries ?? 3;
  }

  async request<TResponse, TBody = unknown>(
    method: Method,
    path: string,
    body?: TBody,
  ): Promise<TResponse> {
    const token = await this.getToken();
    const headers: Record<string, string> = {
      Accept: "application/json",
    };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (method === "POST") headers["Idempotency-Key"] = mintIdempotencyKey();

    const url = `${this.baseUrl}${path.startsWith("/") ? path : `/${path}`}`;
    const init: RequestInit = {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    };

    let lastError: unknown;
    for (let attempt = 0; attempt < this.maxRetries; attempt++) {
      try {
        const res = await this.fetchFn(url, init);
        if (res.ok) {
          // 204 No Content has empty body; return null cast to TResponse.
          if (res.status === 204) return null as TResponse;
          return (await res.json()) as TResponse;
        }
        if (res.status >= 400 && res.status < 500) {
          // Client errors are deterministic — surface immediately.
          throw new ApiError(res.status, await safeText(res), await safeBody(res));
        }
        // 5xx: retry with backoff
        lastError = new ApiError(res.status, `server error ${res.status}`);
      } catch (err) {
        if (err instanceof ApiError && err.status >= 400 && err.status < 500) {
          throw err;
        }
        lastError = err;
      }
      if (attempt < this.maxRetries - 1) {
        await delay(250 * 2 ** attempt);
      }
    }
    if (lastError instanceof ApiError) throw lastError;
    throw new ApiError(0, lastError instanceof Error ? lastError.message : "request failed");
  }

  /** Type-narrowed shortcut for OpenAPI-generated path schemas. */
  async typed<P extends keyof paths, M extends Method, TResponse>(
    method: M,
    path: P,
    body?: unknown,
  ): Promise<TResponse> {
    return this.request<TResponse>(method, path as string, body);
  }
}

async function safeText(res: Response): Promise<string> {
  try {
    return await res.text();
  } catch {
    return `${res.status} ${res.statusText}`;
  }
}

async function safeBody(res: Response): Promise<string | undefined> {
  // Already consumed in safeText path; this branch reached when caller chains.
  // We accept the duplicate read failure silently — message has the gist.
  return undefined;
}

function mintIdempotencyKey(): string {
  // Use crypto.randomUUID where available (modern browsers + Electron 26+).
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // Fallback: timestamp + random — not cryptographically strong, but
  // sufficient as a per-request idempotency marker (uniqueness > entropy).
  return `${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
