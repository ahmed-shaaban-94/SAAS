// Aggregator for typed POS endpoint modules. Consumers do:
//
//   import { createPosApi } from "@pos/api/endpoints";
//   const api = createPosApi(client);
//   await api.transactions.commit({ ... });

import type { ApiClient } from "@pos/api/client";
import { createTransactionEndpoints, type TransactionEndpoints } from "@pos/api/endpoints/transactions";

export interface PosApi {
  transactions: TransactionEndpoints;
}

export function createPosApi(client: ApiClient): PosApi {
  return {
    transactions: createTransactionEndpoints(client),
  };
}
