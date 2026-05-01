// Typed POS shift endpoints (Sub-PR 5).

import type { ApiClient } from "@pos/api/client";
import type { paths } from "@pos/api/types";

type OpenBody =
  paths["/api/v1/pos/shifts"]["post"]["requestBody"] extends
    { content: { "application/json": infer B } }
    ? B
    : never;
type OpenResp =
  paths["/api/v1/pos/shifts"]["post"]["responses"]["201"]["content"]["application/json"];

type CloseBody =
  paths["/api/v1/pos/shifts/{shift_id}/close"]["post"]["requestBody"] extends
    { content: { "application/json": infer B } }
    ? B
    : never;
type CloseResp =
  paths["/api/v1/pos/shifts/{shift_id}/close"]["post"]["responses"]["200"]["content"]["application/json"];

type CurrentResp =
  paths["/api/v1/pos/shifts/current"]["get"]["responses"]["200"]["content"]["application/json"];

type RefreshGrantResp =
  paths["/api/v1/pos/shifts/{shift_id}/refresh-grant"]["post"]["responses"]["200"]["content"]["application/json"];

export interface ShiftEndpoints {
  open: (body: OpenBody) => Promise<OpenResp>;
  close: (shiftId: number, body: CloseBody) => Promise<CloseResp>;
  current: () => Promise<CurrentResp>;
  refreshGrant: (shiftId: number) => Promise<RefreshGrantResp>;
}

export function createShiftEndpoints(client: ApiClient): ShiftEndpoints {
  return {
    open: (body) => client.request("POST", "/api/v1/pos/shifts", body),
    close: (shiftId, body) =>
      client.request("POST", `/api/v1/pos/shifts/${shiftId}/close`, body),
    current: () => client.request("GET", "/api/v1/pos/shifts/current"),
    refreshGrant: (shiftId) =>
      client.request("POST", `/api/v1/pos/shifts/${shiftId}/refresh-grant`, {}),
  };
}
