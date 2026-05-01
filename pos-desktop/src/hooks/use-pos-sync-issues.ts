"use client";

import useSWR from "swr";
import {
  getRejectedQueue,
  reconcileQueue,
  type ReconcileKind,
  type ReconcileResult,
} from "@pos/lib/offline-db";
import type { QueueRow } from "@pos/lib/ipc";

export interface UsePosSyncIssuesResult {
  items: QueueRow[];
  isLoading: boolean;
  isError: boolean;
  mutate: () => Promise<QueueRow[] | undefined>;
  reconcile: (
    localId: string,
    kind: ReconcileKind,
    note: string,
    overrideCode?: string | null,
  ) => Promise<ReconcileResult>;
}

export function usePosSyncIssues(): UsePosSyncIssuesResult {
  const { data, error, isLoading, mutate } = useSWR<QueueRow[]>(
    "pos:queue:rejected",
    getRejectedQueue,
    { refreshInterval: 5_000 },
  );

  async function reconcile(
    localId: string,
    kind: ReconcileKind,
    note: string,
    overrideCode: string | null = null,
  ): Promise<ReconcileResult> {
    const result = await reconcileQueue(localId, kind, note, overrideCode);
    await mutate();
    return result;
  }

  return {
    items: data ?? [],
    isLoading,
    isError: !!error,
    mutate,
    reconcile,
  };
}
