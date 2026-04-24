# `contracts/` — shared API contract

Single source of truth for the HTTP contract between FastAPI and the React
frontend. Closes the drift gap described in issue #658.

## Files

- `openapi.json` — committed. Generated from `datapulse.api.app.create_app()`
  by `scripts/dump_openapi.py`. This file is the **input** to the frontend
  TypeScript codegen at `frontend/src/generated/api.ts`.

## Workflow

Any time you add/change a route, modify a Pydantic response model, or touch
anything that affects the OpenAPI schema:

```bash
# 1. Regenerate the schema
make openapi                           # writes contracts/openapi.json

# 2. Regenerate the TypeScript client from that schema
cd frontend && npm run codegen         # writes frontend/src/generated/api.ts

# 3. Commit both files alongside your backend change
git add contracts/openapi.json frontend/src/generated/api.ts
```

## CI gate

Two check steps prevent the two artifacts from drifting out of sync:

| Job | Step | Command |
|-----|------|---------|
| `typecheck` | Check OpenAPI contract is up to date | `make openapi-check` |
| `frontend`  | Check generated TS client is up to date | `npm run codegen:check` |

A PR that changes a response model without regenerating will fail the
first; one that regenerates the schema but forgets the TS will fail the
second. The failure message points you at the `make` target to run.

## Why commit the artifacts?

- Code review sees the shape changes, not just the Python side.
- The frontend build (including the standalone Docker image) does not need
  Python installed.
- `git blame` on the generated file surfaces when a field appeared/vanished.

## Usage in frontend code

The generated `paths` type covers every endpoint. A small helper at
`frontend/src/lib/api-types.ts` gives ergonomic access:

```ts
import { fetchAPI } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";

// Response type inferred directly from the OpenAPI schema.
const data = await fetchAPI<ApiGet<"/api/v1/analytics/summary">>(
  "/api/v1/analytics/summary",
);
```

No runtime dependency is added; `fetchAPI` and the SWR hooks are unchanged.
