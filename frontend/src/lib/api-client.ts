import { getSession } from "next-auth/react";
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
    if (/^-?\d+(\.\d+)?$/.test(obj)) {
      const n = Number(obj);
      if (Number.isSafeInteger(Math.trunc(n))) return n;
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
 * Retrieve the access token with in-memory caching.
 * Caches for 5 minutes to avoid expensive getSession() calls on every fetch.
 */
let _cachedToken: string | null = null;
let _tokenExpiresAt = 0;
const TOKEN_CACHE_MS = 5 * 60 * 1000; // 5 minutes

async function getAccessToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;

  // Return cached token if still valid
  if (_cachedToken && Date.now() < _tokenExpiresAt) {
    return _cachedToken;
  }

  // Try NextAuth session (Auth0)
  try {
    const session = await getSession();
    if (session?.accessToken) {
      _cachedToken = session.accessToken;
      _tokenExpiresAt = Date.now() + TOKEN_CACHE_MS;
      return _cachedToken;
    }
  } catch {
    // getSession may fail during SSR or before hydration — fall through
  }

  // Fallback: localStorage
  const token = localStorage.getItem("access_token");
  if (token) {
    _cachedToken = token;
    _tokenExpiresAt = Date.now() + TOKEN_CACHE_MS;
  }
  return token;
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
      throw new ApiError(res.status, `API error ${res.status}: ${body}`);
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

export async function postAPI<T>(path: string, body?: unknown): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  return _request<T>(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
