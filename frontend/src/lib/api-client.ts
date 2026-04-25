import { getSession, getLastClerkAuthError } from "@/lib/auth-bridge";
import { API_BASE_URL } from "./constants";
import type { FilterParams } from "@/types/filters";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function parseDecimals(obj: unknown): unknown {
  if (obj === null || obj === undefined) return obj;
  if (typeof obj === "string") {
    // Check if string looks like a decimal number
    if (/^-?\d+(\.\d+)?([eE][+-]?\d+)?$/.test(obj)) {
      const n = Number(obj);
      if (Number.isFinite(n) && (obj.includes(".") || /[eE]/.test(obj) || Number.isSafeInteger(n))) {
        return n;
      }
      return obj;
    }
    return obj;
  }
  if (Array.isArray(obj)) {
    return obj.map(parseDecimals);
  }
  if (typeof obj === "object") {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
      result[key] = parseDecimals(value);
    }
    return result;
  }
  return obj;
}

function buildQueryString(params?: FilterParams): string {
  if (!params) return "";
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      searchParams.set(key, String(value));
    }
  }
  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}

/**
 * Retrieve the current access token from the auth-bridge session.
 * Delegates to getSession() from @/lib/auth-bridge, which works for both
 * Clerk (reads window.Clerk.session) and Auth0/NextAuth (reads the
 * NextAuth session cache). No extra network request on repeated calls;
 * avoids stale-token-after-sign-out that a module-level cache would cause.
 */
async function getAccessToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;

  try {
    const session = await getSession();
    return session?.accessToken ?? null;
  } catch {
    // getSession may fail during SSR or before hydration
    return null;
  }
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  const token = await getAccessToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

/** Shared fetch wrapper handling timeout, error checking, and decimal parsing. */
async function _request<T>(url: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15_000);
  try {
    const authHeaders = await getAuthHeaders();
    const mergedHeaders = { ...authHeaders, ...init?.headers };
    const res = await fetch(url, {
      ...init,
      headers: mergedHeaders,
      signal: controller.signal,
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "Unknown error");
      // When the backend returns 401 AND we failed to attach an
      // Authorization header, the real cause lives in the auth-bridge
      // error stash. Include it so pilots see "Clerk issued a null
      // token — template missing" instead of a bare "401
      // Authentication required". Without this, debugging requires
      // DevTools on an installed build.
      let enriched = `API error ${res.status}: ${body}`;
      if (res.status === 401 && !authHeaders.Authorization) {
        const reason = getLastClerkAuthError();
        if (reason) {
          enriched += ` — ${reason}`;
        } else {
          enriched += " — no Authorization header attached (user not signed in?)";
        }
      }
      throw new ApiError(res.status, enriched);
    }
    const json = await res.json();
    return parseDecimals(json) as T;
  } finally {
    clearTimeout(timeout);
  }
}

export async function fetchAPI<T>(
  path: string,
  params?: FilterParams,
): Promise<T> {
  const url = `${API_BASE_URL}${path}${buildQueryString(params)}`;
  return _request<T>(url);
}

/**
 * Like ``fetchAPI`` but returns ``null`` on a 204 No Content response
 * instead of throwing when attempting to parse an empty body. Intended
 * for endpoints (e.g. ``/ai-light/top-insight``) that legitimately have
 * "no result" as a success state.
 */
export async function fetchAPIOrNull<T>(
  path: string,
  params?: FilterParams,
): Promise<T | null> {
  const url = `${API_BASE_URL}${path}${buildQueryString(params)}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15_000);
  try {
    const authHeaders = await getAuthHeaders();
    const res = await fetch(url, {
      headers: authHeaders,
      signal: controller.signal,
    });
    if (res.status === 204) {
      return null;
    }
    if (!res.ok) {
      const body = await res.text().catch(() => "Unknown error");
      throw new ApiError(res.status, `API error ${res.status}: ${body}`);
    }
    const json = await res.json();
    return parseDecimals(json) as T;
  } finally {
    clearTimeout(timeout);
  }
}

export async function postAPI<T>(
  path: string,
  body?: unknown,
  options?: { headers?: Record<string, string> },
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  return _request<T>(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
}

export async function patchAPI<T>(path: string, body: unknown): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  return _request<T>(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function putAPI<T>(path: string, body: unknown): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  return _request<T>(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function deleteAPI(path: string): Promise<void> {
  const url = `${API_BASE_URL}${path}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15_000);
  try {
    const authHeaders = await getAuthHeaders();
    const res = await fetch(url, {
      method: "DELETE",
      headers: authHeaders,
      signal: controller.signal,
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "Unknown error");
      throw new ApiError(res.status, `API error ${res.status}: ${body}`);
    }
  } finally {
    clearTimeout(timeout);
  }
}

/**
 * Build a stable, order-independent SWR cache key from a path and filter params.
 * Uses sorted URLSearchParams to avoid property-order sensitivity of JSON.stringify.
 */
export function swrKey(path: string, params?: FilterParams): string {
  if (!params) return path;
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) {
      sp.set(k, String(v));
    }
  }
  sp.sort();
  const qs = sp.toString();
  return qs ? `${path}?${qs}` : path;
}

export { ApiError };
