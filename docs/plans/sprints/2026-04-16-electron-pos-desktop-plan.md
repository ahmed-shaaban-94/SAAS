# Plan: Electron POS Desktop App for Windows

## Context

The POS module lives as 5 web pages inside the Next.js frontend (`(pos)` route group). Pharmacy cashiers need a dedicated Windows desktop app that:
- Feels native (taskbar icon, system tray, window controls)
- Connects to the same `smartdatapulse.tech/api/v1/pos/*` backend
- Supports hardware peripherals (barcode scanners, thermal printers) in the future
- Auto-updates without pharmacy visits

The approach: **Electron wrapper** that loads the Next.js standalone server locally, providing 95% code reuse with native capabilities.

## Architecture

```
pos-desktop/
├── package.json              # Electron + electron-builder deps
├── electron/
│   ├── main.ts               # Main process: window, tray, IPC
│   ├── preload.ts            # Context bridge for IPC
│   └── updater.ts            # Auto-update via GitHub Releases
├── assets/
│   ├── icon.ico              # Windows app icon (256x256)
│   ├── icon.png              # Linux/Mac icon
│   └── tray.png              # System tray icon (16x16)
├── electron-builder.yml      # Build config (NSIS installer, auto-update)
├── tsconfig.json             # TypeScript config for electron/
└── scripts/
    └── build.sh              # Build Next.js standalone + package Electron
```

**How it works:**
1. Electron main process starts a local Next.js server (from standalone build)
2. BrowserWindow loads `http://localhost:3847/terminal` (POS pages)
3. Auth0 login opens in the same window (NextAuth handles it)
4. IPC bridge exposes hardware APIs to the renderer (Phase 2)

## Implementation Steps

### Step 1: Scaffold Electron project
Create `pos-desktop/` at project root with:
- `package.json` with electron, electron-builder, typescript deps
- `tsconfig.json` for electron/ directory
- `.gitignore` for dist/, node_modules/, out/

### Step 2: Main process (`electron/main.ts`)
- Create BrowserWindow (1280x800, frameless title bar with DataPulse branding)
- Start Next.js standalone server on port 3847 (random high port)
- Wait for server ready, then load `http://localhost:3847/terminal`
- System tray icon with context menu (Open, Quit)
- Handle window close → minimize to tray (pharmacy keeps it running)
- Graceful shutdown: kill Next.js server on app quit

### Step 3: Preload script (`electron/preload.ts`)
- Expose `window.electronAPI` via contextBridge:
  - `getAppVersion()` — for about dialog
  - `platform` — 'win32'
  - Future: `onBarcodeScanned(callback)`, `printReceipt(data)`

### Step 4: Environment & Auth
- Bundle `.env.production` with:
  - `NEXT_PUBLIC_API_URL=https://smartdatapulse.tech`
  - `NEXTAUTH_URL=http://localhost:3847`
  - `NEXTAUTH_SECRET=<generated>`
  - Auth0 credentials
- Add `http://localhost:3847/api/auth/callback/auth0` to Auth0 allowed callbacks

### Step 5: Build & Package (`electron-builder.yml`)
- Target: Windows NSIS installer (`.exe`)
- App name: "DataPulse POS"
- Auto-update provider: GitHub Releases
- Include Next.js standalone output in `extraResources`
- Code signing: skip for now (add later for Windows SmartScreen)

### Step 6: Build script (`scripts/build.sh`)
```
1. cd frontend && npm run build   (produces .next/standalone/)
2. Copy standalone output to pos-desktop/resources/
3. cd pos-desktop && npm run package  (electron-builder)
4. Output: pos-desktop/dist/DataPulse-POS-Setup.exe
```

## Key Files to Reference

| File | Purpose |
|------|---------|
| `frontend/next.config.mjs` (line 22) | `output: "standalone"` — confirms compatible build |
| `frontend/src/lib/auth.ts` | Auth0 provider config, token refresh logic |
| `frontend/src/app/(pos)/layout.tsx` | POS layout with SessionGuard |
| `frontend/src/lib/api-client.ts` | API communication (uses `NEXT_PUBLIC_API_URL`) |
| `frontend/.env.example` | Required env vars |

## What This Does NOT Include (Phase 2)

- Barcode scanner integration (serial port via `serialport` npm)
- Thermal receipt printing (ESC/POS via `node-thermal-printer`)
- Cash drawer opening (serial trigger)
- Offline mode with local transaction queue
- Windows installer code signing

## Verification

1. `cd pos-desktop && npm install`
2. `cd ../frontend && npm run build` (standalone output)
3. `cd ../pos-desktop && npm start` (dev mode — opens Electron window)
4. Auth0 login should work in the Electron window
5. POS terminal page loads with full functionality
6. `npm run package` produces `dist/DataPulse-POS-Setup.exe`
7. Install on a test Windows machine → app launches, connects to production API
