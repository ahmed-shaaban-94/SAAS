import { buildApiUrl, env } from "../config/env";
import type { ApiErrorShape, HealthStatus, KPISummary } from "../types/api";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function parseDecimals(value: unknown): unknown {
  if (value === null || value === undefined) {
    return value;
  }

  if (typeof value === "string") {
    if (/^-?\d+(\.\d+)?([eE][+-]?\d+)?$/.test(value)) {
      const parsed = Number(value);
      if (
        Number.isFinite(parsed) &&
        (value.includes(".") || /[eE]/.test(value) || Number.isSafeInteger(parsed))
      ) {
        return parsed;
      }
    }
    return value;
  }

  if (Array.isArray(value)) {
    return value.map(parseDecimals);
  }

  if (typeof value === "object") {
    const result: Record<string, unknown> = {};
    for (const [key, entry] of Object.entries(value as Record<string, unknown>)) {
      result[key] = parseDecimals(entry);
    }
    return result;
  }

  return value;
}

async function request<T>(path: string): Promise<T> {
  const headers: Record<string, string> = {};
  if (env.apiKey) {
    headers["X-API-Key"] = env.apiKey;
  }

  const response = await fetch(buildApiUrl(path), { headers });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as ApiErrorShape;
      detail = body.detail || detail;
    } catch {
      detail = await response.text().catch(() => detail);
    }
    throw new ApiError(response.status, detail);
  }

  const json = await response.json();
  return parseDecimals(json) as T;
}

export async function fetchHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/health/ready");
}

export async function fetchSummary(): Promise<KPISummary> {
  return request<KPISummary>("/api/v1/analytics/summary");
}
