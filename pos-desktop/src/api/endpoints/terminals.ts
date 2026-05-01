// Typed POS terminal endpoints (Sub-PR 5).

import type { ApiClient } from "@pos/api/client";
import type { paths } from "@pos/api/types";

type CreateBody =
  paths["/api/v1/pos/terminals"]["post"]["requestBody"] extends
    { content: { "application/json": infer B } }
    ? B
    : never;
type CreateResp =
  paths["/api/v1/pos/terminals"]["post"]["responses"]["201"]["content"]["application/json"];

type ActiveResp =
  paths["/api/v1/pos/terminals/active"]["get"]["responses"]["200"]["content"]["application/json"];

type GetResp =
  paths["/api/v1/pos/terminals/{terminal_id}"]["get"]["responses"]["200"]["content"]["application/json"];

type CloseResp =
  paths["/api/v1/pos/terminals/{terminal_id}/close"]["post"]["responses"]["200"]["content"]["application/json"];

type PauseResp =
  paths["/api/v1/pos/terminals/{terminal_id}/pause"]["post"]["responses"]["200"]["content"]["application/json"];

type ResumeResp =
  paths["/api/v1/pos/terminals/{terminal_id}/resume"]["post"]["responses"]["200"]["content"]["application/json"];

function qs(params: Record<string, unknown>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) usp.set(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

export interface TerminalEndpoints {
  create: (body: CreateBody) => Promise<CreateResp>;
  active: (query: { site_code: string }) => Promise<ActiveResp>;
  get: (terminalId: number) => Promise<GetResp>;
  close: (terminalId: number) => Promise<CloseResp>;
  pause: (terminalId: number) => Promise<PauseResp>;
  resume: (terminalId: number) => Promise<ResumeResp>;
}

export function createTerminalEndpoints(client: ApiClient): TerminalEndpoints {
  return {
    create: (body) => client.request("POST", "/api/v1/pos/terminals", body),
    active: (query) => client.request("GET", `/api/v1/pos/terminals/active${qs(query)}`),
    get: (terminalId) => client.request("GET", `/api/v1/pos/terminals/${terminalId}`),
    close: (terminalId) => client.request("POST", `/api/v1/pos/terminals/${terminalId}/close`, {}),
    pause: (terminalId) => client.request("POST", `/api/v1/pos/terminals/${terminalId}/pause`, {}),
    resume: (terminalId) =>
      client.request("POST", `/api/v1/pos/terminals/${terminalId}/resume`, {}),
  };
}
