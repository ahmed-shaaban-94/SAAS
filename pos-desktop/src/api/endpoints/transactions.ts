// Typed POS transaction endpoints. Wraps ApiClient with OpenAPI-generated
// request/response types. Phase 1 Sub-PR 4 of POS extraction.

import type { ApiClient } from "@pos/api/client";
import type { paths } from "@pos/api/types";

type CreateTransactionResponse =
  paths["/api/v1/pos/transactions"]["post"]["responses"]["200"]["content"]["application/json"];
type AddItemRequest =
  paths["/api/v1/pos/transactions/{transaction_id}/items"]["post"]["requestBody"] extends
    { content: { "application/json": infer B } }
    ? B
    : never;
type AddItemResponse =
  paths["/api/v1/pos/transactions/{transaction_id}/items"]["post"]["responses"]["200"]["content"]["application/json"];
type CommitRequest =
  paths["/api/v1/pos/transactions/commit"]["post"]["requestBody"] extends
    { content: { "application/json": infer B } }
    ? B
    : never;
type CommitResponse =
  paths["/api/v1/pos/transactions/commit"]["post"]["responses"]["200"]["content"]["application/json"];

export interface TransactionEndpoints {
  create: () => Promise<CreateTransactionResponse>;
  addItem: (txnId: number, body: AddItemRequest) => Promise<AddItemResponse>;
  commit: (body: CommitRequest) => Promise<CommitResponse>;
}

export function createTransactionEndpoints(client: ApiClient): TransactionEndpoints {
  return {
    create: () => client.request("POST", "/api/v1/pos/transactions", {}),
    addItem: (txnId, body) =>
      client.request("POST", `/api/v1/pos/transactions/${txnId}/items`, body),
    commit: (body) => client.request("POST", "/api/v1/pos/transactions/commit", body),
  };
}
