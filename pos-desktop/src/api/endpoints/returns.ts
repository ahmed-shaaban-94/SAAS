// Typed POS return endpoints (Sub-PR 5).

import type { ApiClient } from "@pos/api/client";
import type { paths } from "@pos/api/types";

type CreateBody =
  paths["/api/v1/pos/returns"]["post"]["requestBody"] extends
    { content: { "application/json": infer B } }
    ? B
    : never;
type CreateResp =
  paths["/api/v1/pos/returns"]["post"]["responses"]["201"]["content"]["application/json"];

type GetResp =
  paths["/api/v1/pos/returns/{return_id}"]["get"]["responses"]["200"]["content"]["application/json"];

export interface ReturnEndpoints {
  create: (body: CreateBody) => Promise<CreateResp>;
  get: (returnId: number) => Promise<GetResp>;
}

export function createReturnEndpoints(client: ApiClient): ReturnEndpoints {
  return {
    create: (body) => client.request("POST", "/api/v1/pos/returns", body),
    get: (returnId) => client.request("GET", `/api/v1/pos/returns/${returnId}`),
  };
}
