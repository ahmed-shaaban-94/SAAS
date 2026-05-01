"use client";

import { useEffect, useState } from "react";
import { hasElectron, electron } from "@pos/lib/ipc";

export interface OfflineState {
  isOnline: boolean;
  pending: number;
  syncing: number;
  rejected: number;
  unresolved: number;
  lastSyncAt: string | null;
}

const INITIAL_STATE: OfflineState = {
  isOnline: typeof navigator !== "undefined" ? navigator.onLine : true,
  pending: 0,
  syncing: 0,
  rejected: 0,
  unresolved: 0,
  lastSyncAt: null,
};

export function useOfflineState(pollMs = 4000): OfflineState {
  const [state, setState] = useState<OfflineState>(INITIAL_STATE);

  useEffect(() => {
    if (hasElectron()) {
      let active = true;

      const poll = async () => {
        try {
          const s = await electron().sync.state();
          if (!active) return;
          setState({
            isOnline: s.online,
            pending: s.pending,
            syncing: s.syncing,
            rejected: s.rejected,
            unresolved: s.unresolved,
            lastSyncAt: s.last_sync_at,
          });
        } catch {
          // keep last known state on IPC error
        }
      };

      poll();
      const id = setInterval(poll, pollMs);

      return () => {
        active = false;
        clearInterval(id);
      };
    }

    // Browser-only: listen to online/offline events
    const onOnline = () =>
      setState((prev) => ({ ...prev, isOnline: true }));
    const onOffline = () =>
      setState((prev) => ({ ...prev, isOnline: false }));

    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);

    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, [pollMs]);

  return state;
}
