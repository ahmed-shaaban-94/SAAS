import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { router } from "@pos/router";

import "@pos/styles/fonts.css";
import "@pos/styles/globals.css";

// Tray menu navigation bridge: the Electron main process sends "navigate"
// IPC events with a hash path; route them through React Router. No-op
// outside Electron (web preview / dev) since `electronAPI` is undefined.
type ElectronNavBridge = {
  onNavigate?: (callback: (path: string) => void) => () => void;
};
const electronAPI = (window as unknown as { electronAPI?: ElectronNavBridge })
  .electronAPI;
electronAPI?.onNavigate?.((path) => {
  void router.navigate(path);
});

const rootEl = document.getElementById("root");
if (!rootEl) throw new Error("#root not found in index.html");

createRoot(rootEl).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>
);
