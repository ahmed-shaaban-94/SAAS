# M2 Pre-Work — What's in this batch

Pure-code scaffolding for the Electron POS desktop. **No `npm install`
was run** and no native modules were compiled. The next session (M2
proper) picks up here and wires real adapters + runs tests.

## Files added

### Electron main process

| File | Purpose |
|---|---|
| `pos-desktop/electron/db/schema.sql` | Full SQLite schema (products + FTS5, stock, shifts_local, transactions_queue with canonical state machine + signed-envelope fields, sync_state, settings, schema_history, audit_log, secrets_dpapi) |
| `pos-desktop/electron/ipc/contracts.ts` | Typed IPC surface (`ElectronAPI`) shared between main + renderer. Zero third-party deps — types + tiny hand-rolled validators for now. Zod migration is a later task. |
| `pos-desktop/electron/hardware/index.ts` | Factory returning mock or real adapters based on `hardware_mode` setting |
| `pos-desktop/electron/hardware/mock.ts` | Mock printer + drawer adapters with recorded-call logs for Playwright assertions |
| `pos-desktop/electron/sync/queue-state.ts` | Canonical 5-state machine + `isUnresolved` predicate + exponential-backoff next-attempt calc + stats aggregator |
| `pos-desktop/electron/sync/envelope.ts` | Canonical signed-digest builder (§8.9.2). Pure Node crypto — no native deps. |

### Renderer helpers (in `frontend/src/lib/pos/`)

| File | Purpose |
|---|---|
| `scanner-keymap.ts` | `ScannerEngine` state machine + `attachScannerListener` DOM adapter. Timing-based heuristic (≥4 chars within 50 ms ending in Enter = scan). |
| `ipc.ts` | Typed wrapper over `window.electronAPI` with `hasElectron()` guard |
| `offline-db.ts` | Adapter that routes product search + queue stats to Electron IPC or HTTP `fetchAPI` depending on environment |

### Tests (will run once `frontend/` has `npm install`)

| File | Coverage |
|---|---|
| `frontend/src/__tests__/lib/pos/scanner-keymap.test.ts` | 6 tests — engine happy path, gap discard, min-length miss, reset, default config, timeout flush |
| `frontend/src/__tests__/lib/pos/offline-db.test.ts` | 7 tests — IPC path, HTTP fallback, 404→null, non-404 rethrow, queue stats parity |

## What's deliberately NOT done (deferred to M2 proper)

1. `npm install` of any new dep
2. `better-sqlite3` wiring — `db/schema.sql` is ready but the connection + migration runner + prepared-statement helpers need the native module compiled
3. Real hardware adapters (`node-thermal-printer`, `serialport`, `node-hid`)
4. DPAPI secret storage (Windows-only native module)
5. Next.js server bootstrap changes in `main.ts` beyond what's already scaffolded
6. `electron-updater` wiring
7. Sentry integration
8. Jest/ts-jest config for the main process
9. Playwright E2E scenarios
10. `preload.ts` IPC surface expansion — current stubs need to be replaced with typed `contextBridge.exposeInMainWorld` calls matching the `ElectronAPI` interface

## How to pick up M2 proper

```bash
cd pos-desktop
# 1. Install Windows Build Tools (one-time, machine-wide):
#    npm install --global windows-build-tools
# 2. Add native deps declared in package.json._m2Notes.plannedRuntimeDeps:
npm install better-sqlite3 node-thermal-printer electron-updater
# 3. Add dev deps + test infra:
npm install --save-dev jest ts-jest @types/jest @types/better-sqlite3 electron-rebuild
# 4. Rebuild native modules for the Electron ABI:
npx electron-rebuild
# 5. Wire real adapters into hardware/index.ts (switch 'real' branch)
# 6. Implement db/connection.ts + db/migrate.ts against better-sqlite3
# 7. Expand preload.ts to register every handler declared in ipc/contracts.ts
```

Then run `frontend/npm install` + `frontend/npx vitest run src/__tests__/lib/pos` to
confirm the pre-work tests are green.

## Self-review

- [x] Pure TypeScript / SQL only — no third-party imports that would require `npm install`
- [x] All files reference design sections by number for traceability
- [x] Renderer helpers correctly guard on `hasElectron()` so browser builds don't crash
- [x] Queue state machine exhaustively lists transitions (no "or else" branches)
- [x] Mock hardware records every call for E2E assertions
- [x] Schema comment blocks explain the decimal-as-string convention + unresolved predicate
- [x] No secrets or placeholders ("TODO", "TBD", fill-me-in)
