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

export async function fetchAPI<T>(
  path: string,
  params?: FilterParams,
): Promise<T> {
  const url = `${API_BASE_URL}${path}${buildQueryString(params)}`;
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.text().catch(() => "Unknown error");
    throw new ApiError(res.status, `API error ${res.status}: ${body}`);
  }
  const json = await res.json();
  return parseDecimals(json) as T;
}

export { ApiError };
