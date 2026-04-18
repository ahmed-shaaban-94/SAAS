/**
 * Preload script — runs in the renderer with Node.js access.
 * Exposes the full `window.electronAPI` surface via contextBridge.
 *
 * Every channel name here must have a matching ipcMain.handle() in
 * electron/ipc/handlers.ts.  The types mirror ElectronAPI from
 * electron/ipc/contracts.ts — kept inline so the Next.js build does not
 * need to import from pos-desktop/.
 *
 * Design ref: docs/superpowers/specs/2026-04-17-pos-electron-desktop-design.md §4.3.
 */

import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("electronAPI", {
  // ── db ─────────────────────────────────────────────────────
  db: {
    "products.search": (q: string, limit?: number) =>
      ipcRenderer.invoke("db.products.search", q, limit),

    "products.byCode": (drugCode: string) =>
      ipcRenderer.invoke("db.products.byCode", drugCode),

    "stock.forDrug": (drugCode: string, siteCode: string) =>
      ipcRenderer.invoke("db.stock.forDrug", drugCode, siteCode),

    "queue.enqueue": (input: unknown) =>
      ipcRenderer.invoke("db.queue.enqueue", input),

    "queue.pending": () => ipcRenderer.invoke("db.queue.pending"),

    "queue.rejected": () => ipcRenderer.invoke("db.queue.rejected"),

    "queue.stats": () => ipcRenderer.invoke("db.queue.stats"),

    "queue.reconcile": (
      localId: string,
      kind: string,
      note: string,
      overrideCode: string | null,
    ) => ipcRenderer.invoke("db.queue.reconcile", localId, kind, note, overrideCode),

    "shifts.current": () => ipcRenderer.invoke("db.shifts.current"),

    "shifts.open": (payload: unknown) =>
      ipcRenderer.invoke("db.shifts.open", payload),

    "shifts.close": (payload: unknown) =>
      ipcRenderer.invoke("db.shifts.close", payload),

    "settings.get": (key: string) =>
      ipcRenderer.invoke("db.settings.get", key),

    "settings.set": (key: string, value: string) =>
      ipcRenderer.invoke("db.settings.set", key, value),
  },

  // ── printer ────────────────────────────────────────────────
  printer: {
    print: (payload: unknown) => ipcRenderer.invoke("printer.print", payload),
    status: () => ipcRenderer.invoke("printer.status"),
    testPrint: () => ipcRenderer.invoke("printer.testPrint"),
  },

  // ── drawer ─────────────────────────────────────────────────
  drawer: {
    open: () => ipcRenderer.invoke("drawer.open"),
  },

  // ── sync ───────────────────────────────────────────────────
  sync: {
    pushNow: () => ipcRenderer.invoke("sync.pushNow"),
    pullNow: (entity?: string) => ipcRenderer.invoke("sync.pullNow", entity),
    state: () => ipcRenderer.invoke("sync.state"),
  },

  // ── authz ──────────────────────────────────────────────────
  authz: {
    currentGrant: () => ipcRenderer.invoke("authz.currentGrant"),
    grantState: () => ipcRenderer.invoke("authz.grantState"),
    refreshGrant: () => ipcRenderer.invoke("authz.refreshGrant"),
    consumeOverrideCode: (code: string) =>
      ipcRenderer.invoke("authz.consumeOverrideCode", code),
    capabilities: () => ipcRenderer.invoke("authz.capabilities"),
  },

  // ── updater ────────────────────────────────────────────────
  updater: {
    check: () => ipcRenderer.invoke("updater.check"),
    install: () => ipcRenderer.invoke("updater.install"),
  },

  // ── app ────────────────────────────────────────────────────
  app: {
    version: () => ipcRenderer.invoke("app.version"),
    logsPath: () => ipcRenderer.invoke("app.logsPath"),
    platform: process.platform,
    isElectron: true as const,
  },

  // ── barcode scanner events ─────────────────────────────────
  onBarcodeScanned: (callback: (barcode: string) => void): (() => void) => {
    const listener = (_event: Electron.IpcRendererEvent, barcode: string) =>
      callback(barcode);
    ipcRenderer.on("barcode-scanned", listener);
    return () => ipcRenderer.removeListener("barcode-scanned", listener);
  },
});
