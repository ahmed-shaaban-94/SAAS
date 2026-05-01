import { app, BrowserWindow, Tray, Menu, nativeImage, shell } from "electron";
import * as path from "path";
import { openDb } from "./db/connection";
import { applySchema } from "./db/migrate";
import { createHardware } from "./hardware/index";
import { registerIpcHandlers } from "./ipc/handlers";
import { getSetting } from "./db/settings";
import { bootRecovery, startBackgroundSync } from "./sync/background";
import { getBaseUrl } from "./sync/push";
import { setupUpdater, checkForUpdates } from "./updater/index";
import { upgradeSecretsToEncrypted } from "./authz/secure-store";
import { createLogger } from "./logging/index";
import { initSentry, isCrashReportingEnabled } from "./observability/sentry";

// ── Configuration ──────────────────────────────────────────
// Renderer source after Vite migration (Sub-PR 2 of POS extraction):
//   - Production: load static Vite bundle from `dist/renderer/index.html`
//     via Electron `loadFile`. No embedded Node server, no remote origin —
//     the bundle is shipped inside the installer and runs offline-first.
//     Clerk auth happens via the live API; the renderer origin is `file://`,
//     for which Clerk needs the redirect URL allowlist updated to match.
//   - Dev: when DATAPULSE_DEV_RENDERER_URL is set, point at the Vite dev
//     server (default http://localhost:5173). Hot reload + source maps.
//   - Remote-renderer fallback (rollback escape hatch): when
//     DATAPULSE_REMOTE_RENDERER_URL is set, load that URL via loadURL.
//     Used by the rollback path if the static bundle ships broken.
const DEV_RENDERER_URL = process.env.DATAPULSE_DEV_RENDERER_URL;
const REMOTE_RENDERER_URL = process.env.DATAPULSE_REMOTE_RENDERER_URL;
const POS_HASH_PATH = "#/terminal";
const APP_TITLE = "DataPulse POS";

// ── State ──────────────────────────────────────────────────
let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let isQuitting = false;

// Logger is created lazily — `app.getPath('logs')` requires Electron
// to be fully initialised, so we defer file-destination wiring until
// after `app.whenReady()`. `release` / `environment` are stamped on the
// first call (the singleton below ignores deps on re-entry) so every
// log line correlates with the matching Sentry event's release tag.
const RESOLVED_RELEASE = app.getVersion();
const RESOLVED_ENVIRONMENT =
  process.env.DATAPULSE_ENV ?? (app.isPackaged ? "production" : "development");
// Pre-ready logger: stdout only (no worker thread, no file lock).
// `app.getPath('logs')` is not resolvable yet, so we can't start the
// rotating file logger here. A second `createLogger({ reinit: true })`
// call inside `app.whenReady()` swaps in the real file-backed instance.
//
// We MUST force `pretty: true` for this pre-ready call. If we used
// `!app.isPackaged` here, production builds would create a worker-backed
// pino-roll transport at module load, then another one at reinit — both
// pointed at the same log file. The two workers race for the file lock,
// one ends, and the next `log.info()` crashes the main process with
// "Error: the worker is ending". (Reproduced on the v3 smoke build.)
let log = createLogger({
  pretty: true,
  release: RESOLVED_RELEASE,
  environment: RESOLVED_ENVIRONMENT,
});

// ── Paths ──────────────────────────────────────────────────
function getRendererIndexHtml(): string {
  // After the Vite migration, the renderer ships as a static bundle.
  // In packaged app: resources/renderer/index.html (electron-builder
  // extraResources copies dist/renderer there).
  // In dev: dist/renderer/index.html (produced by `vite build`) when
  // DATAPULSE_DEV_RENDERER_URL is unset; otherwise the dev server URL
  // is used directly via loadURL.
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "renderer", "index.html");
  }
  return path.join(__dirname, "..", "..", "dist", "renderer", "index.html");
}

function getAssetsDir(): string {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "assets");
  }
  return path.join(__dirname, "..", "assets");
}

// ── Renderer ───────────────────────────────────────────────
// After Vite migration: load the static bundle via `loadFile` (prod) or the
// Vite dev server URL (dev). No Node.js subprocess; no Next.js standalone.
// The bundle uses HashRouter, so /terminal is reachable via `#/terminal`
// regardless of whether the URL scheme is `file://` or `http://`.

function loadRenderer(window: BrowserWindow): Promise<void> {
  if (DEV_RENDERER_URL) {
    log.info({ url: DEV_RENDERER_URL }, "loading dev renderer");
    return window.loadURL(`${DEV_RENDERER_URL}${POS_HASH_PATH}`);
  }
  if (REMOTE_RENDERER_URL) {
    log.info({ url: REMOTE_RENDERER_URL }, "loading remote renderer (rollback path)");
    return window.loadURL(`${REMOTE_RENDERER_URL}${POS_HASH_PATH}`);
  }
  const indexHtml = getRendererIndexHtml();
  log.info({ indexHtml }, "loading static Vite bundle");
  return window.loadFile(indexHtml, { hash: POS_HASH_PATH.replace(/^#/, "") });
}

// ── Window ─────────────────────────────────────────────────
function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1024,
    minHeight: 700,
    title: APP_TITLE,
    icon: path.join(getAssetsDir(), "icon.png"),
    backgroundColor: "#0a0e1a",
    show: false, // Show after content loads
    // Hide menu bar in production; keep visible in dev for easy reload
    autoHideMenuBar: app.isPackaged,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      // DevTools enabled in packaged builds during the Phase 1 stabilization
      // window — pharmacists need a way to surface launch errors without
      // flashing an env var (#824 will gate this back to !isPackaged for GA).
      // Press Ctrl+Shift+I in the running app to inspect.
      devTools: true,
    },
  });

  // Show window once content is ready (avoids white flash)
  mainWindow.once("ready-to-show", () => {
    mainWindow?.show();
    mainWindow?.focus();
  });

  // Load the renderer (Vite static bundle in prod, Vite dev server in dev,
  // or a remote rollback URL when DATAPULSE_REMOTE_RENDERER_URL is set).
  void loadRenderer(mainWindow);

  // Renderer load failure surfacing — without an embedded fallback server
  // we can no longer self-recover, but we MUST surface the failure so the
  // pilot doesn't sit on a blank window. Sentry already captures the event
  // via the renderer-crash bridge for online users; this handler logs the
  // raw Chromium error code locally so a tech can grep the log file.
  mainWindow.webContents.on(
    "did-fail-load",
    (_event, errorCode, errorDescription, validatedURL, isMainFrame) => {
      if (!isMainFrame) return;
      log.error(
        { errorCode, errorDescription, validatedURL },
        "renderer load failed — bundle missing or static asset 404",
      );
    },
  );

  // Mirror renderer console messages (errors + warnings) into the main-
  // process log so a black-screen launch leaves a paper trail without the
  // user having to open DevTools. Useful when CSP / runtime exceptions
  // happen before Sentry can connect.
  mainWindow.webContents.on(
    "console-message",
    (_event, level, message, line, sourceId) => {
      // 0=verbose, 1=info, 2=warning, 3=error
      if (level >= 2) {
        log.warn(
          { level, sourceId, line, message },
          "renderer console",
        );
      }
    },
  );

  // Hash-router routes (createHashRouter): the URL is `file:///.../index.html#/<path>`.
  // The path-based redirect logic from the Next.js era is no longer needed;
  // React Router owns navigation entirely within the rendered page.

  // Open external links in the system browser. The static-bundle origin is
  // `file://` and the dev server is `http://localhost:5173`; both are
  // implicitly internal. Only Clerk hosted pages need an allowlist so the
  // sign-in flow can navigate inside the Electron window without bouncing
  // out to the OS browser.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    const parsed = new URL(url);
    const internalHost =
      parsed.protocol === "file:" ||
      parsed.hostname === "localhost" ||
      parsed.hostname.endsWith(".clerk.accounts.dev") ||
      parsed.hostname.endsWith(".clerk.com");
    if (!internalHost) {
      shell.openExternal(url);
    }
    return { action: "deny" };
  });

  // Minimize to tray instead of closing
  mainWindow.on("close", (event) => {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow?.hide();
    }
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

// ── System Tray ────────────────────────────────────────────
function createTray(): void {
  const iconPath = path.join(getAssetsDir(), "tray.png");
  let trayIcon: Electron.NativeImage;
  try {
    trayIcon = nativeImage.createFromPath(iconPath);
  } catch {
    // Fallback: create a simple 16x16 icon
    trayIcon = nativeImage.createEmpty();
  }

  tray = new Tray(trayIcon);
  tray.setToolTip(APP_TITLE);

  const contextMenu = Menu.buildFromTemplate([
    {
      label: "Open DataPulse POS",
      click: () => {
        mainWindow?.show();
        mainWindow?.focus();
      },
    },
    { type: "separator" },
    {
      label: "Terminal",
      click: () => {
        mainWindow?.show();
        mainWindow?.webContents.send("navigate", "/terminal");
      },
    },
    {
      label: "Shift Management",
      click: () => {
        mainWindow?.show();
        mainWindow?.webContents.send("navigate", "/shift");
      },
    },
    {
      label: "Transaction History",
      click: () => {
        mainWindow?.show();
        mainWindow?.webContents.send("navigate", "/history");
      },
    },
    { type: "separator" },
    {
      label: `v${app.getVersion()}`,
      enabled: false,
    },
    {
      label: "Quit",
      click: () => {
        isQuitting = true;
        app.quit();
      },
    },
  ]);

  tray.setContextMenu(contextMenu);

  tray.on("double-click", () => {
    mainWindow?.show();
    mainWindow?.focus();
  });
}

// ── App Lifecycle ──────────────────────────────────────────
app.whenReady().then(async () => {
  // Re-create the logger now that Electron's `app` is ready, so file output
  // goes to the platform-correct logs path instead of cwd. `reinit: true`
  // replaces the pre-ready cached instance — without it the singleton guard
  // in `createLogger` would silently hand back the first logger and `logsDir`
  // would be ignored in production. `release` + `environment` are stamped
  // so every log line carries the same values as the matching Sentry event.
  log = createLogger({
    logsDir: app.getPath("logs"),
    pretty: !app.isPackaged,
    release: RESOLVED_RELEASE,
    environment: RESOLVED_ENVIRONMENT,
    reinit: true,
  });
  log.info({ version: app.getVersion() }, "DataPulse POS starting");

  // Initialise local SQLite database
  const dbPath = path.join(app.getPath("userData"), "pos.db");
  const db = openDb(dbPath);
  applySchema(db, undefined, app.getVersion());
  log.info({ dbPath }, "SQLite database ready");

  // M3b hardening: upgrade any plaintext (v0 / legacy) secrets to DPAPI-wrapped
  // storage in-place. Idempotent — already-encrypted rows are skipped.
  try {
    const upgraded = upgradeSecretsToEncrypted(db);
    if (upgraded > 0) {
      log.info({ upgraded }, "upgraded secrets from plain to encrypted storage");
    }
  } catch (err) {
    log.error({ err }, "secure-store upgrade failed (continuing boot)");
  }

  // Crash reporting — opt-in only (issue #481). Scrub PII inside `initSentry`.
  // The SDK is dynamically imported, so opted-out pilots never pay the cost.
  try {
    if (isCrashReportingEnabled(db)) {
      const dsn = process.env.SENTRY_DSN;
      if (dsn) {
        await initSentry({
          dsn,
          release: RESOLVED_RELEASE,
          environment: RESOLVED_ENVIRONMENT,
        });
        log.info({ release: RESOLVED_RELEASE }, "crash reporting enabled");
      } else {
        log.warn(
          "crash reporting requested but SENTRY_DSN is unset — skipping init",
        );
      }
    }
  } catch (err) {
    log.error({ err }, "crash reporting init failed (continuing boot)");
  }

  // Initialise hardware adapters (mock or real based on settings)
  const hardwareMode = getSetting(db, "hardware_mode");
  const printerInterface = getSetting(db, "printer_interface") ?? undefined;
  const printerType = getSetting(db, "printer_type") ?? undefined;
  const hw = createHardware(
    hardwareMode === "real" ? "real" : "mock",
    printerInterface ? { printerInterface, printerType } : undefined,
  );
  log.info({ mode: hw.mode }, "hardware mode resolved");

  // Reset any syncing rows orphaned by a previous crash (§6.1 boot recovery)
  bootRecovery(db);

  // Register all IPC handlers before windows are created
  registerIpcHandlers(db, hw);

  // Renderer source is selected at load-time (see `loadRenderer`):
  // dev server / remote rollback / static bundle. No server-side wait
  // needed — Vite produces a static bundle and the dev server is the
  // user's responsibility to start (`npm run dev:vite`).
  if (DEV_RENDERER_URL) {
    log.info({ url: DEV_RENDERER_URL }, "dev renderer mode");
  } else if (REMOTE_RENDERER_URL) {
    log.info({ url: REMOTE_RENDERER_URL }, "remote renderer rollback mode");
  } else {
    log.info("static renderer mode (Vite bundle via loadFile)");
  }

  createWindow();

  // Dev: open DevTools immediately + enable hot-reload via webContents reload
  if (!app.isPackaged && mainWindow) {
    mainWindow.webContents.openDevTools({ mode: "detach" });
  }
  createTray();

  // Wire auto-updater after window is ready (only in packaged builds)
  if (mainWindow && app.isPackaged) {
    setupUpdater(mainWindow);
    // Delay the first check 30s so it doesn't compete with startup I/O
    setTimeout(() => {
      checkForUpdates({
        baseUrl: getBaseUrl(),
        jwt: getSetting(db, "jwt"),
        currentVersion: app.getVersion(),
        channel: "stable",
        platform: process.platform,
      }).catch(() => {});
    }, 30_000);
  }

  // Start background sync loop (push queue every 10s, online detection via /health)
  const stopSync = startBackgroundSync(db, mainWindow);
  app.on("before-quit", stopSync);

  app.on("activate", () => {
    // macOS: re-create window when dock icon clicked
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("before-quit", () => {
  isQuitting = true;
});

app.on("window-all-closed", () => {
  // On macOS, apps stay active until Cmd+Q
  if (process.platform !== "darwin") {
    isQuitting = true;
    app.quit();
  }
});

// Prevent multiple instances
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    // Focus existing window if user tries to open a second instance
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });
}
