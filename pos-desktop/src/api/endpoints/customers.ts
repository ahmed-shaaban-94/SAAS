// Typed POS customer endpoints (Sub-PR 5).

import type { ApiClient } from "@pos/api/client";
import type { paths } from "@pos/api/types";

type LookupResp =
  paths["/api/v1/pos/customers/by-phone/{phone}"]["get"]["responses"]["200"]["content"]["application/json"];

export interface CustomerEndpoints {
  byPhone: (phone: string) => Promise<LookupResp>;
}

export function createCustomerEndpoints(client: ApiClient): CustomerEndpoints {
  return {
    byPhone: (phone) =>
      client.request("GET", `/api/v1/pos/customers/by-phone/${encodeURIComponent(phone)}`),
  };
}
