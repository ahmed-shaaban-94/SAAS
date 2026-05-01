// Typed POS promotion endpoints (Sub-PR 5).

import type { ApiClient } from "@pos/api/client";
import type { paths } from "@pos/api/types";

type EligibleBody =
  paths["/api/v1/pos/promotions/eligible"]["post"]["requestBody"] extends
    { content: { "application/json": infer B } }
    ? B
    : never;
type EligibleResp =
  paths["/api/v1/pos/promotions/eligible"]["post"]["responses"]["200"]["content"]["application/json"];

export interface PromotionEndpoints {
  eligible: (body: EligibleBody) => Promise<EligibleResp>;
}

export function createPromotionEndpoints(client: ApiClient): PromotionEndpoints {
  return {
    eligible: (body) => client.request("POST", "/api/v1/pos/promotions/eligible", body),
  };
}
