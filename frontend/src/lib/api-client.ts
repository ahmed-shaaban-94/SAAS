import { API_BASE_URL } from "./constants";
import type { FilterParams } from "@/types/filters";

const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  if (API_KEY) headers["X-API-Key"] = API_KEY;
  return headers;
}

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

export async function fetchAPI<T>(
  path: string,
  params?: FilterParams,
): Promise<T> {
  const url = `${API_BASE_URL}${path}${buildQueryString(params)}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30_000);
  try {
    const res = await fetch(url, { headers: authHeaders(), signal: controller.signal });
    if (!res.ok) {
      const body = await res.text().catch(() => "Unknown error");
      throw new ApiError(res.status, `API error ${res.status}: ${body}`);
    }
    const json = await res.json();
    return parseDecimals(json) as T;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function postAPI<T>(path: string, body?: unknown): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30_000);
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
    if (!res.ok) {
      const errText = await res.text().catch(() => "Unknown error");
      throw new ApiError(res.status, `API error ${res.status}: ${errText}`);
    }
    const json = await res.json();
    return parseDecimals(json) as T;
  } finally {
    clearTimeout(timeoutId);
  }
}

export { ApiError };
