// Aggregator for typed POS endpoint modules. Consumers do:
//
//   import { createPosApi } from "@pos/api/endpoints";
//   const api = createPosApi(client);
//   await api.transactions.commit({ ... });

import type { ApiClient } from "@pos/api/client";
import {
  createCustomerEndpoints,
  type CustomerEndpoints,
} from "@pos/api/endpoints/customers";
import { createDrugEndpoints, type DrugEndpoints } from "@pos/api/endpoints/drugs";
import {
  createProductEndpoints,
  type ProductEndpoints,
} from "@pos/api/endpoints/products";
import {
  createPromotionEndpoints,
  type PromotionEndpoints,
} from "@pos/api/endpoints/promotions";
import { createReturnEndpoints, type ReturnEndpoints } from "@pos/api/endpoints/returns";
import { createShiftEndpoints, type ShiftEndpoints } from "@pos/api/endpoints/shifts";
import {
  createTerminalEndpoints,
  type TerminalEndpoints,
} from "@pos/api/endpoints/terminals";
import {
  createTransactionEndpoints,
  type TransactionEndpoints,
} from "@pos/api/endpoints/transactions";
import {
  createVoucherEndpoints,
  type VoucherEndpoints,
} from "@pos/api/endpoints/vouchers";

export interface PosApi {
  customers: CustomerEndpoints;
  drugs: DrugEndpoints;
  products: ProductEndpoints;
  promotions: PromotionEndpoints;
  returns: ReturnEndpoints;
  shifts: ShiftEndpoints;
  terminals: TerminalEndpoints;
  transactions: TransactionEndpoints;
  vouchers: VoucherEndpoints;
}

export function createPosApi(client: ApiClient): PosApi {
  return {
    customers: createCustomerEndpoints(client),
    drugs: createDrugEndpoints(client),
    products: createProductEndpoints(client),
    promotions: createPromotionEndpoints(client),
    returns: createReturnEndpoints(client),
    shifts: createShiftEndpoints(client),
    terminals: createTerminalEndpoints(client),
    transactions: createTransactionEndpoints(client),
    vouchers: createVoucherEndpoints(client),
  };
}
