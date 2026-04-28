# Archived Frontend Routes

These route directories have been moved out of the Next.js build.
They do not compile, type-check, or run tests.

To restore a category:
1. Move its directory back to `frontend/src/app/`
2. Set `archived: false` (or remove the flag) on its NAV_GROUP in `frontend/src/lib/constants.ts`
3. Commit the change

## Archived categories

| Category | Original path | Archived date |
|---|---|---|
| Control Center | `app/control-center/` | 2026-04-28 |
| Operations | `app/{inventory,dispensing,expiry,purchase-orders,suppliers}/` | 2026-04-28 |
| Intelligence | `app/{insights,alerts,scenarios}/` | 2026-04-28 |
