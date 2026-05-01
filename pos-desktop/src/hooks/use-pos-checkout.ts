import { useState } from "react";
import { patchAPI, postAPI } from "@shared/lib/api-client";
import type {
  TransactionCreateRequest,
  AddItemRequest,
  UpdateItemRequest,
  CheckoutRequest,
  CheckoutResponse,
  PosCartItem,
  VoidRequest,
  TransactionResponse,
} from "@pos/types/pos";

interface CheckoutState {
  transactionId: number | null;
  isLoading: boolean;
  error: string | null;
}

export function usePosCheckout() {
  const [state, setState] = useState<CheckoutState>({
    transactionId: null,
    isLoading: false,
    error: null,
  });

  function setLoading(isLoading: boolean) {
    setState((s) => ({ ...s, isLoading, error: null }));
  }

  function setError(error: string) {
    setState((s) => ({ ...s, isLoading: false, error }));
  }

  async function createTransaction(
    req: TransactionCreateRequest,
  ): Promise<TransactionResponse> {
    setLoading(true);
    try {
      // Backend expects terminal_id, site_code etc. as query params (not body)
      const qs = new URLSearchParams({ terminal_id: String(req.terminal_id), site_code: req.site_code });
      if (req.customer_id) qs.set("customer_id", req.customer_id);
      const txn = await postAPI<TransactionResponse>(`/api/v1/pos/transactions?${qs}`);
      setState({ transactionId: txn.id, isLoading: false, error: null });
      return txn;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create transaction");
      throw e;
    }
  }

  async function addItem(
    transactionId: number,
    req: AddItemRequest,
  ): Promise<PosCartItem> {
    setLoading(true);
    try {
      // Backend requires Idempotency-Key on POST /transactions/{id}/items
      // since #799. Without it the request 422s with
      // {"loc":["header","Idempotency-Key"],"msg":"Field required"}.
      // Mint a fresh UUID per call so a retried add at the network layer
      // (e.g. flaky offline-online transition) doesn't duplicate the line.
      const idempotencyKey =
        typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
          ? crypto.randomUUID()
          : `ai-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      // Defensive String() on drug_code: the AddItemRequest type says string,
      // but a numeric SKU coming from a search response or a stale offline
      // cart can leak through as a JS number — backend pydantic rejects
      // {"input": 3210570, "msg": "Input should be a valid string"}.
      const safeReq: AddItemRequest = {
        ...req,
        drug_code: String(req.drug_code),
      };
      const item = await postAPI<PosCartItem>(
        `/api/v1/pos/transactions/${transactionId}/items`,
        safeReq,
        { headers: { "Idempotency-Key": idempotencyKey } },
      );
      setState((s) => ({ ...s, isLoading: false }));
      return item;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add item");
      throw e;
    }
  }

  async function updateItem(
    transactionId: number,
    itemId: number,
    req: UpdateItemRequest,
  ): Promise<PosCartItem> {
    return patchAPI<PosCartItem>(
      `/api/v1/pos/transactions/${transactionId}/items/${itemId}`,
      req,
    );
  }

  async function removeItem(
    transactionId: number,
    itemId: number,
  ): Promise<void> {
    const { deleteAPI } = await import("@shared/lib/api-client");
    await deleteAPI(`/api/v1/pos/transactions/${transactionId}/items/${itemId}`);
  }

  async function checkout(
    transactionId: number,
    req: CheckoutRequest,
  ): Promise<CheckoutResponse> {
    setLoading(true);
    try {
      // Audit C1: the backend now requires Idempotency-Key on /checkout so a
      // network-layer retry can't double-charge. Mint a fresh UUID per
      // user-initiated checkout; the server dedupes replays for 168h.
      const idempotencyKey =
        typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
          ? crypto.randomUUID()
          : `ck-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      const res = await postAPI<CheckoutResponse>(
        `/api/v1/pos/transactions/${transactionId}/checkout`,
        req,
        { headers: { "Idempotency-Key": idempotencyKey } },
      );
      setState({ transactionId: null, isLoading: false, error: null });
      return res;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Checkout failed");
      throw e;
    }
  }

  async function voidTransaction(
    transactionId: number,
    req: VoidRequest,
  ): Promise<TransactionResponse> {
    return postAPI<TransactionResponse>(
      `/api/v1/pos/transactions/${transactionId}/void`,
      req,
    );
  }

  return {
    ...state,
    createTransaction,
    addItem,
    updateItem,
    removeItem,
    checkout,
    voidTransaction,
  };
}
