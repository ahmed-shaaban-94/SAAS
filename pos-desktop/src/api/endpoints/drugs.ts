// Typed POS drug clinical endpoints (Sub-PR 5).

import type { ApiClient } from "@pos/api/client";
import type { paths } from "@pos/api/types";

type DetailResp =
  paths["/api/v1/pos/drugs/{drug_code}"]["get"]["responses"]["200"]["content"]["application/json"];
type AltResp =
  paths["/api/v1/pos/drugs/{drug_code}/alternatives"]["get"]["responses"]["200"]["content"]["application/json"];
type CrossSellResp =
  paths["/api/v1/pos/drugs/{drug_code}/cross-sell"]["get"]["responses"]["200"]["content"]["application/json"];

export interface DrugEndpoints {
  detail: (drugCode: string) => Promise<DetailResp>;
  alternatives: (drugCode: string) => Promise<AltResp>;
  crossSell: (drugCode: string) => Promise<CrossSellResp>;
}

export function createDrugEndpoints(client: ApiClient): DrugEndpoints {
  return {
    detail: (drugCode) => client.request("GET", `/api/v1/pos/drugs/${drugCode}`),
    alternatives: (drugCode) =>
      client.request("GET", `/api/v1/pos/drugs/${drugCode}/alternatives`),
    crossSell: (drugCode) => client.request("GET", `/api/v1/pos/drugs/${drugCode}/cross-sell`),
  };
}
