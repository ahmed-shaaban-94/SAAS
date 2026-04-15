import { postAPI } from "@/lib/api-client";
import type { ReturnRequest, ReturnResponse, VoidResponse } from "@/types/pos";

export async function processReturn(req: ReturnRequest): Promise<ReturnResponse> {
  return postAPI<ReturnResponse>("/api/v1/pos/returns", req);
}

export async function voidTransaction(
  transactionId: number,
  reason: string,
): Promise<VoidResponse> {
  return postAPI<VoidResponse>(`/api/v1/pos/transactions/${transactionId}/void`, { reason });
}
