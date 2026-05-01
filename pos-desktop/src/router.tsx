// React Router setup for the POS shell — replaces Next.js App Router after
// the Vite migration. createHashRouter is required because Electron's
// loadFile() serves index.html via file:// where browser-history routing
// (createBrowserRouter) fails on refresh.

import { createHashRouter, Navigate, Outlet } from "react-router-dom";
import PosLayout from "@pos/pages/layout";
import TerminalPage from "@pos/pages/terminal";
import CheckoutPage from "@pos/pages/checkout";
import ShiftPage from "@pos/pages/shift";
import DrugsPage from "@pos/pages/drugs";
import HistoryPage from "@pos/pages/history";
import PosReturnsPage from "@pos/pages/pos-returns";
import SyncIssuesPage from "@pos/pages/sync-issues";

export const router = createHashRouter([
  {
    element: (
      <PosLayout>
        <Outlet />
      </PosLayout>
    ),
    children: [
      { index: true, element: <Navigate to="/terminal" replace /> },
      { path: "/terminal", element: <TerminalPage /> },
      { path: "/checkout", element: <CheckoutPage /> },
      { path: "/shift", element: <ShiftPage /> },
      { path: "/drugs", element: <DrugsPage /> },
      { path: "/history", element: <HistoryPage /> },
      { path: "/pos-returns", element: <PosReturnsPage /> },
      { path: "/sync-issues", element: <SyncIssuesPage /> },
    ],
  },
]);
