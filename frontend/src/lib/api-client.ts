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
 * Retrieve the access token.
 * Tries the NextAuth session first (Keycloak OIDC), then falls back to
 * localStorage for backwards compatibility (e.g. API-key based auth).
 */
async function getAccessToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;

  // Try NextAuth session (Keycloak)
  try {
    const session = await getSession();
    if (session?.accessToken) return session.accessToken;
  } catch {
    // getSession may fail during SSR or before hydration — fall through
  }

  // Fallback: localStorage
  return localStorage.getItem("access_token");
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
