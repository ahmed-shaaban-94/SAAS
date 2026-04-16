import { useState } from "react";
import { patchAPI, postAPI } from "@/lib/api-client";
import type {
  TransactionCreateRequest,
  AddItemRequest,
  UpdateItemRequest,
  CheckoutRequest,
  CheckoutResponse,
  PosCartItem,
  VoidRequest,
  TransactionResponse,
} from "@/types/pos";

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
      const item = await postAPI<PosCartItem>(
        `/api/v1/pos/transactions/${transactionId}/items`,
        req,
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
    const { deleteAPI } = await import("@/lib/api-client");
    await deleteAPI(`/api/v1/pos/transactions/${transactionId}/items/${itemId}`);
  }

  async function checkout(
    transactionId: number,
    req: CheckoutRequest,
  ): Promise<CheckoutResponse> {
    setLoading(true);
    try {
      const res = await postAPI<CheckoutResponse>(
        `/api/v1/pos/transactions/${transactionId}/checkout`,
        req,
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
