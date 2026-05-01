"use client";

/**
 * JWT-to-SQLite bridge for the POS Desktop shell.
 *
 * The Electron sync workers (pullProducts, pullStock, push queue) read the
 * Clerk JWT from the local SQLite settings table — `getSetting(db, "jwt")`.
 * Nothing was writing to that key until this hook landed, so the local
 * catalog stayed empty even after a successful Clerk sign-in.
 *
 * Contract:
 *   • Runs only inside the Electron POS shell (no-op in the browser).
 *   • Polls `getSession().accessToken` every {@link POLL_INTERVAL_MS}.
 *   • Writes via `electronAPI.db.settings.set("jwt", token)` only on change
 *     to avoid hammering the SQLite WAL with identical writes.
 *   • Clears the stored token on sign-out so background sync stops.
 *
 * Why polling instead of an event subscription?
 *   `auth-bridge.tsx` exposes `useSession()` with `data.accessToken`, but
 *   Clerk rotates tokens on its own ~60-second cadence; the React state
 *   only re-renders the consumer when the SDK refreshes internally. A
 *   poll guarantees freshness independent of consumer re-renders, which
 *   is what the SQLite-backed sync workers need.
 */

import { useEffect, useRef } from "react";

import { useSession } from "@/lib/auth-bridge";
import { db as posDb, hasElectron } from "@pos/lib/ipc";

const POLL_INTERVAL_MS = 30_000;
const JWT_SETTING_KEY = "jwt";

export function useJwtBridge(): void {
  const { data, status } = useSession();
  const lastWrittenRef = useRef<string | null>(null);

  useEffect(() => {
    if (!hasElectron()) return;

    let cancelled = false;

    async function syncToken() {
      if (cancelled) return;
      if (status !== "authenticated") {
        // Clear on sign-out so sync workers stop trying.
        if (lastWrittenRef.current !== null) {
          try {
            await posDb.settings.set(JWT_SETTING_KEY, "");
            lastWrittenRef.current = null;
          } catch {
            // SQLite write errors are non-fatal — a stale JWT will surface
            // as a 401 on the next sync attempt and the worker logs it.
          }
        }
        return;
      }

      const token = data?.accessToken ?? null;
      if (!token) return;
      if (token === lastWrittenRef.current) return;

      try {
        await posDb.settings.set(JWT_SETTING_KEY, token);
        lastWrittenRef.current = token;
      } catch {
        // See above — non-fatal; do not block the renderer.
      }
    }

    void syncToken();
    const id = setInterval(() => {
      void syncToken();
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [data, status]);
}
