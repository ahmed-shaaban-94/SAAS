import { contextBridge, ipcRenderer } from "electron";

/**
 * Preload script — runs in the renderer process with access to Node.js APIs.
 * Exposes a safe `window.electronAPI` object via contextBridge.
 *
 * Phase 1: version info + platform detection
 * Phase 2: barcode scanner events, receipt printing, cash drawer
 */
contextBridge.exposeInMainWorld("electronAPI", {
  /** App version from package.json */
  getAppVersion: (): Promise<string> => ipcRenderer.invoke("get-app-version"),

  /** Running platform ('win32', 'darwin', 'linux') */
  platform: process.platform,

  /** Whether running inside Electron (vs browser) */
  isElectron: true,

  // ── Phase 2: Hardware APIs (stubs) ──────────────────────
  // onBarcodeScanned: (callback: (barcode: string) => void) => {
  //   ipcRenderer.on("barcode-scanned", (_event, barcode) => callback(barcode));
  // },
  // printReceipt: (data: unknown) => ipcRenderer.invoke("print-receipt", data),
  // openCashDrawer: () => ipcRenderer.invoke("open-cash-drawer"),
});
