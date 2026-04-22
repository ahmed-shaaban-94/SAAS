import { app, BrowserWindow, Tray, Menu, nativeImage, shell } from "electron";
import { ChildProcess, spawn } from "child_process";
import * as path from "path";
import * as http from "http";
import { openDb } from "./db/connection";
import { applySchema } from "./db/migrate";
import { createHardware } from "./hardware/index";
import { registerIpcHandlers } from "./ipc/handlers";
import { getSetting } from "./db/settings";
import { bootRecovery, startBackgroundSync } from "./sync/background";
import { setupUpdater, checkForUpdates } from "./updater/index";
import { upgradeSecretsToEncrypted } from "./authz/secure-store";
import { createLogger } from "./logging/index";
import { initSentry, isCrashReportingEnabled } from "./observability/sentry";

// ── Configuration ──────────────────────────────────────────
const PORT = 3847;
// In dev, set DATAPULSE_DEV_RENDERER_URL=http://localhost:3000 to connect to
// `next dev` directly instead of starting a standalone server.
const DEV_RENDERER_URL = process.env.DATAPULSE_DEV_RENDERER_URL;
const NEXTJS_URL = DEV_RENDERER_URL ?? `http://localhost:${PORT}`;
const POS_PATH = "/terminal";
const APP_TITLE = "DataPulse POS";

// ── State ──────────────────────────────────────────────────
let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let nextServer: ChildProcess | null = null;
let isQuitting = false;

// Logger is created lazily — `app.getPath('logs')` requires Electron
// to be fully initialised, so we defer file-destination wiring until
// after `app.whenReady()`. `release` / `environment` are stamped on the
// first call (the singleton below ignores deps on re-entry) so every
// log line correlates with the matching Sentry event's release tag.
const RESOLVED_RELEASE = app.getVersion();
const RESOLVED_ENVIRONMENT =
  process.env.DATAPULSE_ENV ?? (app.isPackaged ? "production" : "development");
let log = createLogger({
  pretty: !app.isPackaged,
  release: RESOLVED_RELEASE,
  environment: RESOLVED_ENVIRONMENT,
});

// ── Paths ──────────────────────────────────────────────────
function getNextJsDir(): string {
  // In packaged app: resources/nextjs/
  // In dev: first try resources/nextjs (copied by build script),
  //         then fall back to frontend/.next/standalone/
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "nextjs");
  }
  const resourcesDir = path.join(__dirname, "..", "..", "resources", "nextjs");
  const devDir = path.join(__dirname, "..", "..", "..", "frontend", ".next", "standalone");
  // Prefer the copied resources dir (built via build.sh)
  try {
    require("fs").accessSync(path.join(resourcesDir, "server.js"));
    return resourcesDir;
  } catch {
    return devDir;
  }
}

function getAssetsDir(): string {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "assets");
  }
  return path.join(__dirname, "..", "assets");
}

// ── Next.js Server ─────────────────────────────────────────
function startNextServer(): Promise<void> {
  return new Promise((resolve, reject) => {
    const nextDir = getNextJsDir();
    const serverScript = path.join(nextDir, "server.js");

    log.info({ serverScript }, "starting Next.js server");

    // Set env vars for the Next.js server.
    // All Auth0 + API vars are passed through from the Electron process env
    // so a single .env file at the pos-desktop root controls everything.
    const env = {
      ...process.env,
      PORT: String(PORT),
      HOSTNAME: "localhost",
      NODE_ENV: "production",
      NEXTAUTH_URL: `http://localhost:${PORT}`,
      NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "https://smartdatapulse.tech",
      INTERNAL_API_URL: process.env.INTERNAL_API_URL || "https://smartdatapulse.tech",
    };

    // Use spawn('node') instead of fork() — Electron's fork() uses the
    // Electron binary as the Node interpreter which doesn't work for
    // plain Node.js scripts like Next.js server.js
    nextServer = spawn("node", [serverScript], {
      cwd: nextDir,
      env,
      stdio: "pipe",
      shell: false,
    });

    nextServer.stdout?.on("data", (data: Buffer) => {
      const msg = data.toString().trim();
      if (msg) log.info({ source: "next" }, msg);
    });

    nextServer.stderr?.on("data", (data: Buffer) => {
      const msg = data.toString().trim();
      if (msg) log.error({ source: "next" }, msg);
    });

    nextServer.on("error", (err) => {
      log.error({ err }, "failed to start Next.js server");
      reject(err);
    });

    nextServer.on("exit", (code) => {
      log.info({ code }, "Next.js server exited");
      nextServer = null;
      if (!isQuitting) {
        // Server crashed — show error and quit
        app.quit();
      }
    });

    // Poll until the server is ready
    waitForServer(resolve, reject, 30_000);
  });
}

function waitForServer(
  resolve: () => void,
  reject: (err: Error) => void,
  timeoutMs: number,
): void {
  const start = Date.now();
  const check = () => {
    if (Date.now() - start > timeoutMs) {
      reject(new Error("Next.js server did not start within timeout"));
      return;
    }
    http
      .get(`${NEXTJS_URL}/api/auth/session`, (res) => {
        if (res.statusCode && res.statusCode < 500) {
          log.info({ status: res.statusCode }, "Next.js server ready");
          resolve();
        } else {
          setTimeout(check, 500);
        }
        res.resume(); // Consume response data
      })
      .on("error", () => {
        setTimeout(check, 500);
      });
  };
  check();
}

function stopNextServer(): void {
  if (nextServer) {
    log.info("stopping Next.js server");
    nextServer.kill("SIGTERM");
    nextServer = null;
  }
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
      // Disable devtools shortcuts in packaged builds
      devTools: !app.isPackaged,
    },
  });

  // Show window once content is ready (avoids white flash)
  mainWindow.once("ready-to-show", () => {
    mainWindow?.show();
    mainWindow?.focus();
  });

  // Load POS terminal page
  mainWindow.loadURL(`${NEXTJS_URL}${POS_PATH}`);

  // POS navigation guard — after auth callback, redirect back to POS
  // instead of landing on the dashboard or marketing page.
  const POS_ROUTES = ["/terminal", "/checkout", "/shift", "/history", "/pos-returns", "/login", "/api/auth"];
  mainWindow.webContents.on("did-navigate", (_event, url) => {
    try {
      const parsed = new URL(url);
      const path = parsed.pathname;
      const isPosRoute = POS_ROUTES.some((r) => path.startsWith(r));
      if (!isPosRoute && parsed.hostname === "localhost") {
        log.info({ from: path }, "redirecting back to POS terminal");
        mainWindow?.loadURL(`${NEXTJS_URL}${POS_PATH}`);
      }
    } catch { /* ignore parse errors */ }
  });

  // Open external links (Auth0, etc.) in the same window — don't open system browser
  // Auth0 Universal Login needs to render inside the Electron window.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    // Only block truly external links (not Auth0)
    const parsed = new URL(url);
    if (!parsed.hostname.includes("auth0") && !parsed.hostname.includes("localhost")) {
      shell.openExternal(url);
      return { action: "deny" };
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
        mainWindow?.loadURL(`${NEXTJS_URL}/terminal`);
      },
    },
    {
      label: "Shift Management",
      click: () => {
        mainWindow?.show();
        mainWindow?.loadURL(`${NEXTJS_URL}/shift`);
      },
    },
    {
      label: "Transaction History",
      click: () => {
        mainWindow?.show();
        mainWindow?.loadURL(`${NEXTJS_URL}/history`);
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
  applySchema(db);
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

  if (DEV_RENDERER_URL) {
    // Dev mode: frontend is served by `next dev` — just wait for it to be ready.
    log.info({ url: DEV_RENDERER_URL }, "dev mode: waiting for Next.js dev server");
    await new Promise<void>((resolve, reject) =>
      waitForServer(resolve, reject, 30_000),
    );
  } else {
    try {
      await startNextServer();
    } catch (err) {
      log.fatal({ err }, "cannot start Next.js server");
      app.quit();
      return;
    }
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
    setTimeout(() => { checkForUpdates().catch(() => {}); }, 30_000);
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
  stopNextServer();
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
