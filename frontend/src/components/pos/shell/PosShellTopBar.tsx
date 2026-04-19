"use client";

import { useRouter, usePathname } from "next/navigation";
import { useSession } from "next-auth/react";
import { useOfflineState } from "@/hooks/use-offline-state";
import { TopBar } from "./TopBar";
import type { PosScreen } from "./TabSwitcher";

const PATH_TO_SCREEN: Record<string, PosScreen> = {
  "/terminal": "terminal",
  "/sync-issues": "sync",
  "/shift": "shift",
  "/drugs": "drugs",
  // `/checkout`, `/history`, `/pos-returns` are sub-flows of Terminal for now.
  "/checkout": "terminal",
  "/history": "terminal",
  "/pos-returns": "terminal",
};

const SCREEN_TO_PATH: Record<PosScreen, string> = {
  terminal: "/terminal",
  sync: "/sync-issues",
  shift: "/shift",
  // `drugs` is introduced in a later PR; route safely to terminal until then.
  drugs: "/terminal",
};

/**
 * Wrapper that wires `TopBar` into the live POS session state:
 *   - screen derived from pathname
 *   - online / queueDepth from useOfflineState
 *   - cashier from NextAuth session
 *
 * Kept separate from `TopBar` so tests can exercise the pure presentational
 * component without mocking hooks.
 */
export function PosShellTopBar() {
  const router = useRouter();
  const pathname = usePathname();
  const { isOnline, unresolved } = useOfflineState();
  const { data: session } = useSession();

  const screen: PosScreen = pathname
    ? (PATH_TO_SCREEN[pathname] ?? inferScreenFromPath(pathname))
    : "terminal";

  const cashierName = session?.user?.name ?? session?.user?.email ?? "—";

  return (
    <TopBar
      screen={screen}
      online={isOnline}
      queueDepth={unresolved}
      cashierName={cashierName}
      onSwitchScreen={(next) => router.push(SCREEN_TO_PATH[next])}
      tabBadges={unresolved > 0 ? { sync: unresolved } : undefined}
    />
  );
}

function inferScreenFromPath(pathname: string): PosScreen {
  for (const [prefix, screen] of Object.entries(PATH_TO_SCREEN)) {
    if (pathname.startsWith(prefix)) return screen;
  }
  return "terminal";
}
