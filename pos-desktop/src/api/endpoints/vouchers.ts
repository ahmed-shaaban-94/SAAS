// Typed POS voucher endpoints (Sub-PR 5).

import type { ApiClient } from "@pos/api/client";
import type { paths } from "@pos/api/types";

type ValidateBody =
  paths["/api/v1/pos/vouchers/validate"]["post"]["requestBody"] extends
    { content: { "application/json": infer B } }
    ? B
    : never;
type ValidateResp =
  paths["/api/v1/pos/vouchers/validate"]["post"]["responses"]["200"]["content"]["application/json"];

export interface VoucherEndpoints {
  validate: (body: ValidateBody) => Promise<ValidateResp>;
}

export function createVoucherEndpoints(client: ApiClient): VoucherEndpoints {
  return {
    validate: (body) => client.request("POST", "/api/v1/pos/vouchers/validate", body),
  };
}
