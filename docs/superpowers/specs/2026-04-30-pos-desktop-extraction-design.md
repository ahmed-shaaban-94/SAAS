# POS Desktop Extraction & Pipeline Standardization — Design

**Date:** 2026-04-30
**Author:** Claude (Opus 4.7) with Ahmed Shaaban
**Status:** Approved — ready for implementation plan
**Scope:** 2 phased PRs (Phase 2 first ~3 days, Phase 1 next ~1 week) + 2-week observation gate
**Models recommended:** Sonnet 4.6 for both phases; escalate to Opus only for the cart-store unification design call

## 1. Why this exists

A long evening of POS work surfaced a structural problem: tonight's incidents weren't bad luck, they were symptoms of accumulated mess.

- **Stuck-container deploy loop** ([incident note](../../brain/incidents/2026-04-30-stuck-container-deploy-loop.md)) — fixed in [PR #800](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/800)
- **Charge → 422 "no items"** — fixed in [PR #798](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/798)
- **Charge → 422 missing Idempotency-Key + numeric drug_code** — fixed in [PR #801](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/801)
- **Tag pushed → no GitHub Release published, silent fail** — fixed in [PR #802](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/802)

Each fix was correct in isolation. Together they exposed five recurring root causes:

1. **POS code is split across three layers** — web frontend (`frontend/src/app/(pos)/`, `frontend/src/components/pos/`), embedded Next.js standalone (`pos-desktop/resources/nextjs/` baked at build time), and Electron (`pos-desktop/electron/`). Drift between layers causes silent fails.
2. **Cart state lives in two client-side stores plus the backend** — Zustand store at `frontend/src/store/pos-cart-store.ts` AND React context at `frontend/src/contexts/pos-cart-context.tsx`, neither synced to the backend transaction until Charge fires. Source of tonight's bulk-sync regression — items existed on the client but not on the server-side draft.
3. **Per-release SQL migrations** — every desktop release needs a hand-written migration to register itself in `pos.desktop_update_releases`. Easy to forget; we forgot tonight.
4. **Workflow assumes `package.json.version` is correct** — git tag and `package.json` can disagree silently. Silent skip of every artifact when they do.
5. **Code-signing not configured** — every cashier sees a Windows SmartScreen warning on first install.

This spec proposes a phased, reversible fix: **standardize the release pipeline first (Phase 2), then extract POS into a focused module (Phase 1)**, then operate for 2 weeks before deciding whether a full repo fork is warranted.

## 2. Goals & non-goals

### Goals

1. **Eliminate the silent-fail mode** in the desktop release pipeline (tag/version assertion).
2. **Eliminate per-release SQL migrations** by replacing them with an authenticated admin endpoint.
3. **Configure code-signing** so cashier installs don't trigger SmartScreen.
4. **Extract POS to a focused module** that owns its own build, state, and styles — drops the embedded Next.js standalone layer.
5. **Unify cart state** to a single Zustand store; delete duplicates.
6. **Preserve every working behavior** users rely on — POS routes, components, offline sync, auto-updater, receipts, today's Gemini visual port.
7. **Phased & reversible** — Phase 2 is cheap and shippable on its own; Phase 1 only proceeds if Phase 2 doesn't already calm the system.

### Non-goals

- **Full repo fork** — explicitly deferred until Phase 3 measurement says it's needed.
- **Backend redesign** — REST API, RLS, dbt models stay unchanged.
- **Web dashboard changes** — analytics, settings, RBAC admin, Power BI integration untouched.
- **New features** — this is structural, not feature work.
- **Migration of receipt printing logic** — already clean, just relocated.
- **Auto-updater redesign** — already correct, just relocated.

## 3. Architecture: before & after

### Before (current state)

```
Data-Pulse/
├── frontend/                       # Next.js dashboard + embedded POS
│   └── src/
│       ├── app/(pos)/              # 8 POS routes
│       ├── components/pos/         # ~25 POS components
│       ├── hooks/use-pos-*         # ~15 POS hooks
│       ├── contexts/pos-cart-context.tsx  # ONE of three cart stores
│       ├── store/pos-cart-store.ts        # TWO of three cart stores
│       └── app/globals.css         # POS tokens mixed with dashboard tokens
└── pos-desktop/                    # Electron app
    ├── electron/                   # main, preload, IPC, updater, sync
    ├── resources/nextjs/           # ← BAKED AT BUILD TIME — embedded Next.js standalone
    └── scripts/build.sh            # Builds frontend/, copies into resources/, then packages
```

Build flow: `npm build (frontend/)` → copy standalone → `tsc (pos-desktop/electron/)` → `electron-builder package`.

### After Phase 2 (pipeline standardized)

Same module shape — only the workflow + a new endpoint change:

```
.github/workflows/pos-desktop-release.yml  ← gains tag/version assert + register-rollout step + signing
src/datapulse/api/routes/_pos_admin_releases.py  ← NEW — POST /api/v1/pos/admin/desktop-releases
```

### After Phase 1 (extraction complete)

```
Data-Pulse/
├── frontend/                       # ← dashboard only (POS deleted from here)
│   └── src/
│       ├── app/(dashboard)/        # analytics, settings, RBAC etc.
│       └── app/globals.css         # ← POS tokens removed
├── pos-desktop/                    # ← focused, owns its own build
│   ├── src/
│   │   ├── pages/                  # was app/(pos)/
│   │   │   ├── terminal.tsx
│   │   │   ├── checkout.tsx
│   │   │   ├── shift.tsx
│   │   │   ├── drugs.tsx
│   │   │   ├── history.tsx
│   │   │   ├── pos-returns.tsx
│   │   │   └── sync-issues.tsx
│   │   ├── components/             # was components/pos/
│   │   │   ├── terminal/           # cart, scan, totals, modals (~17 files)
│   │   │   ├── receipts/           # sales, insurance, delivery, thermal (~6 files)
│   │   │   └── modals/             # checkout, shift, manager-pin, voucher (~6 files)
│   │   ├── hooks/                  # was hooks/use-pos-*
│   │   │   ├── use-pos-cart.ts     # thin wrapper over the unified store
│   │   │   ├── use-pos-checkout.ts
│   │   │   ├── use-pos-products.ts
│   │   │   ├── use-pos-customer-lookup.ts
│   │   │   ├── use-pos-drug-clinical.ts
│   │   │   ├── use-active-shift.ts
│   │   │   ├── use-offline-state.ts
│   │   │   └── use-manager-override.ts
│   │   ├── store/
│   │   │   └── cart-store.ts       # THE one cart store — Zustand
│   │   ├── api/                    # NEW — typed REST client
│   │   │   ├── client.ts           # auth + retry + Idempotency-Key
│   │   │   ├── types.ts            # generated from contracts/openapi.json
│   │   │   └── endpoints/
│   │   │       ├── transactions.ts
│   │   │       ├── shifts.ts
│   │   │       ├── products.ts
│   │   │       └── ...
│   │   ├── electron/               # unchanged — main, preload, IPC, updater, sync
│   │   └── styles/
│   │       └── globals.css         # POS tokens only
│   ├── vite.config.ts              # NEW — replaces Next.js for the renderer
│   ├── electron-builder.yml        # ← drops the resources/nextjs extraResources block
│   ├── package.json                # version bumped to 3.0.0 (clean-break signal)
│   └── tsconfig.json
└── contracts/openapi.json          # ← shared, unchanged
```

Build flow after Phase 1: `vite build (pos-desktop/src/)` → `tsc (pos-desktop/electron/)` → `electron-builder package`. **No more Next.js standalone server in the desktop app.**

## 4. Phase 2 — Pipeline standardization (~3 days, 1 PR)

### 4.1 Tag/version assertion

In `.github/workflows/pos-desktop-release.yml`, add a step before the build:

```yaml
- name: Assert tag matches package.json version
  if: startsWith(github.ref, 'refs/tags/pos-desktop-v')
  shell: bash
  run: |
    TAG_VERSION="${GITHUB_REF#refs/tags/pos-desktop-v}"
    PKG_VERSION=$(node -p "require('./pos-desktop/package.json').version")
    if [ "$TAG_VERSION" != "$PKG_VERSION" ]; then
      cat <<EOF
::error::Tag version mismatch
  Tag:           pos-desktop-v$TAG_VERSION
  package.json:  $PKG_VERSION

Recovery:
  1. Bump pos-desktop/package.json + package-lock.json to $TAG_VERSION
  2. Commit + push to main
  3. Delete bad tag: git push origin :refs/tags/pos-desktop-v$TAG_VERSION
  4. Re-tag from new HEAD: git tag pos-desktop-v$TAG_VERSION && git push origin pos-desktop-v$TAG_VERSION
EOF
      exit 1
    fi
    echo "::notice::Tag and package.json both at $TAG_VERSION"
```

This eliminates tonight's silent-fail mode permanently. The error message contains the runbook.

### 4.2 Auto-register rollout endpoint

New FastAPI route in `src/datapulse/api/routes/_pos_admin_releases.py`:

```python
@router.post(
    "/api/v1/pos/admin/desktop-releases",
    status_code=201,
    response_model=DesktopReleaseResponse,
)
async def register_desktop_release(
    body: DesktopReleaseCreate,
    user: CurrentUser = Depends(require_permission("pos:update:manage")),
    session: AsyncSession = Depends(get_async_session),
) -> DesktopReleaseResponse:
    """Idempotent — INSERT … ON CONFLICT DO UPDATE. The release workflow
    calls this after a successful publish to GitHub Releases. Replaces
    the per-release SQL migration pattern (#797–#802 used migration 123)."""
    ...
```

- Behind `pos:update:manage` permission (already exists in `migration 115`)
- Idempotent — workflow can call N times safely
- Validates: version is non-empty, channel ∈ {`stable`, `beta`}, platform ∈ {`win32`, `darwin`, `linux`}, rollout_scope ∈ {`all`, `selected`, `paused`}
- Returns 201 with the inserted/updated row

Workflow step that calls it after publish:

```yaml
- name: Register rollout in DB
  if: success() && startsWith(github.ref, 'refs/tags/pos-desktop-v')
  env:
    POS_ADMIN_TOKEN: ${{ secrets.POS_ADMIN_TOKEN }}
  shell: bash
  run: |
    VERSION="${GITHUB_REF#refs/tags/pos-desktop-v}"
    curl -fsSL --retry 3 -X POST https://smartdatapulse.tech/api/v1/pos/admin/desktop-releases \
      -H "Authorization: Bearer $POS_ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d "$(jq -nc \
        --arg v "$VERSION" \
        '{version:$v,channel:"stable",platform:"win32",rollout_scope:"all",active:true}')"
```

A new `POS_ADMIN_TOKEN` GitHub secret is required (operator generates a Bearer with `pos:update:manage`).

### 4.3 Code-signing config (#476)

- Add `CSC_LINK` (base64-encoded `.pfx`) and `CSC_KEY_PASSWORD` to repo secrets — operator step, not code
- The workflow already detects them; no code change needed beyond confirming the detection block runs and the existing signature-verify step gates on it
- Document the cert-rotation cadence in `docs/ops/key-rotation.md` (existing runbook)

### 4.4 Phase 2 testing

- Unit tests for the new endpoint — auth gate, idempotency, validation
- Integration test (docker-compose harness): mock `POST /admin/desktop-releases` → assert DB row exists + idempotent re-call doesn't dup
- E2E manual: tag a `pos-desktop-v0.0.0-test` build on a throwaway branch, watch the entire pipeline run end-to-end
- Workflow assertion: deliberately push a tag that disagrees with package.json — confirm the workflow fails fast with the recovery message

## 5. Phase 1 — POS extraction (~1 week, multiple sub-PRs)

Phase 1 only proceeds **after Phase 2 ships and is healthy for ≥1 release cycle**. If Phase 2 alone calms the system, Phase 3 may decide to defer Phase 1.

### 5.1 Pre-extraction recon (parallel subagents)

Before any file moves, four parallel `Explore` subagents map the dependency graph. This is the **decision input** for the keep/drop list.

| Subagent | Task |
|---|---|
| Recon-imports | Find every import from `frontend/src/{components,hooks,contexts,store}/pos*` to non-pos files; list reverse direction too |
| Recon-tests | Find every test file that touches POS code; categorize as terminal-flow / receipt / shift / utility |
| Recon-assets | Find every `public/` asset, font, icon referenced by POS components |
| Recon-styles | Find every `globals.css` selector, custom property, and Tailwind utility used only by POS |

Output: a single `recon-output.md` consolidating findings into:

- **Keep list** — files imported by an active `(pos)` route
- **Drop list** — orphan files in `components/pos/` not reachable from any active route
- **Merge list** — duplicate components or hooks (e.g., two cart stores) that need consolidation
- **Cross-cut list** — non-pos files that import from `pos/*` and need rewriting

User reviews the lists before any move happens.

### 5.2 Module move (sequential)

After recon, three sequential sub-PRs (each independently mergeable):

#### Sub-PR 1: Mechanical move — `git mv` + import fixes (1–2 days)

- `git mv` everything on the keep list to the new locations under `pos-desktop/src/`
- Fix imports — bulk codemod replacing `@/components/pos/...` → `@/pos-desktop/components/...`
- Drop everything on the drop list
- Smoke test: existing test suite passes; existing `pos-desktop/scripts/build.sh --dev` still produces a runnable Electron app
- The Electron app **still uses the embedded Next.js standalone** at this point — only file paths changed

#### Sub-PR 2: Replace embedded Next.js with static React build (2–3 days)

- Add `vite.config.ts` and `index.html` to `pos-desktop/`
- Convert each `pages/*.tsx` from Next.js page conventions to a Vite-rendered React Router setup
- `electron/main.ts` switches from spawning `node server.js` to `BrowserWindow.loadFile('dist/index.html')`
- Delete `pos-desktop/resources/nextjs/`, `pos-desktop/scripts/build.sh`'s standalone-copy step, the `extraResources` block in `electron-builder.yml`
- The bundled installer becomes ~30% smaller (no embedded Node server)
- Smoke test: app launches → loads UI → IPC works → backend calls work

#### Sub-PR 3: Cart-store unification (1–2 days)

- Decide which of the two existing stores survives (likely `frontend/src/store/pos-cart-store.ts` since `usePosCart` is widely used; the React context becomes a thin wrapper or is deleted)
- Move the surviving store to `pos-desktop/src/store/cart-store.ts`
- Snapshot tests: assert the unified store's behavior matches every existing call-site (recon list pre-populated)
- Delete the duplicate
- This is the change with the highest risk — escalate to Opus model for design call if the snapshot tests reveal subtle behavior diffs

### 5.3 Typed API client (bundled into Sub-PR 1 or its own small PR)

- Run `openapi-typescript ../contracts/openapi.json -o pos-desktop/src/api/types.ts` (the script already exists)
- Wrap fetch with auth + Idempotency-Key minting + retry — replaces ad-hoc `postAPI` / `fetchAPI` calls
- Endpoint modules per resource (`endpoints/transactions.ts`, etc.) — typed wrappers around the raw client

### 5.4 Phase 1 testing

- All existing POS tests must pass after every sub-PR (gate)
- New cart store: snapshot tests asserting parity with the old behavior across the 14 call-sites the recon agent found
- Electron smoke test: app launches, loads the new static React build, no IPC errors, no missing-asset 404s
- Manual cashier walkthrough on staging: open shift → scan drug → quick-pick → voucher apply → checkout cash → checkout card → shift close → receipt prints
- Hard gate: tagged `pos-desktop-v3.0.0-rc1` build on staging-only DB row (rollout_scope='selected' + one tenant) — manual install on a test machine, full shift run

## 6. Phase 3 — Observe & decide (2 weeks, no code)

After Phase 1 ships, run the new system live for 2 weeks. Hard deadline.

### 6.1 Metrics to track

| Metric | Target | Source |
|---|---|---|
| Release-pipeline incidents (silent fails, manual hotfixes) | 0 | this incident log |
| Time-to-rollout (tag pushed → first cashier sees update) | <1 hour | release workflow timestamps + `pos.desktop_update_releases.created_at` |
| Cashier support tickets re: install / update | <2 / week | support inbox |
| Surprise bugs at deploy time | 0 P1, ≤1 P2 / week | brain note pattern |
| Developer pain reports ("noisy and messy" sentiment) | qualitative — explicit ask at week 2 | direct user check-in |

### 6.2 Decision gate

End of week 2, write `docs/brain/decisions/2026-05-14-pos-extraction-outcome.md` answering:

- Did the structural pain stop?
- What's still messy?
- Do we still want a separate repo, or did extraction alone solve it?

Three possible outcomes:

- **Calm** → keep extracted module, close out this initiative
- **Still noisy in pipeline** → another scoped fix; do NOT fork yet
- **Still noisy in code** → fork to a separate repo, with the recon + extraction work already done as a clean starting point

## 7. Subagent dispatch plan

Per `superpowers:dispatching-parallel-agents` rules, dispatch only when work is **independent**.

| Stage | Agent type | Parallel? | Task |
|---|---|---|---|
| Phase 2 endpoint design | `feature-dev:code-architect` | no | Sequential after spec approval — designs the endpoint shape |
| Phase 2 implementation | single executor (this session) | no | Workflow + endpoint + signing — too small for parallelism |
| Phase 2 review | `code-reviewer` | no | Reviews the PR before merge |
| Phase 1 recon | `Explore` (×4) | **yes** | imports / tests / assets / styles — independent searches |
| Phase 1 module shape | `feature-dev:code-architect` | no | Sequential after recon — designs new directory layout |
| Phase 1 sub-PR 1 (move) | single executor | no | Mechanical, sequential |
| Phase 1 sub-PR 2 (Vite migration) | single executor | no | Sequential — depends on sub-PR 1 |
| Phase 1 sub-PR 3 (cart unification) | single executor + `tdd-guide` | no | Sequential, TDD |
| Per-sub-PR review | `code-reviewer` | no | Independent reviews per sub-PR (each PR isolated) |
| Phase 3 measurement | none | n/a | Just operate |

**Estimated parallel speedup:** Phase 1 recon stage saves ~2 hours by running 4 explorations concurrently. Beyond that, sequential dependencies dominate; agent dispatch is for review and architecture rather than throughput.

## 8. Risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Phase 1 migration breaks the running web POS | medium | high | Keep web POS routes alive as redirects to "open desktop app" for 2 weeks; only delete after Phase 3 calm |
| Embedded Next.js → static React loses an SSR feature we relied on | low | medium | Audit current POS routes for SSR usage in recon stage — POS is highly client-side, expected to find none |
| Cart-store unification loses a behavior | medium | high | Snapshot tests against existing 3-store behavior; assert unified store covers every recon-mapped call-site |
| Phase 2 endpoint creates new attack surface | low | medium | RBAC-gated (`pos:update:manage`), already-existing permission, threat model unchanged |
| Code-signing cert rotation forgotten | medium | low | Add to `docs/ops/key-rotation.md` cadence list |
| `POS_ADMIN_TOKEN` leaked from CI logs | low | high | Set as masked secret; `gh secret set` with `--app actions`; never echo in workflow |
| Phase 3 observation window stalls forever | medium | low | Calendar deadline: 2026-05-14 brain note is mandatory |
| Phase 1 sub-PRs land out of order | low | high | Stack PRs explicitly; CI gates each on previous merge to main |

## 9. Files touched

### Phase 2 (~12 files)

```
.github/workflows/pos-desktop-release.yml                        (modify — add 2 steps)
src/datapulse/api/routes/_pos_admin_releases.py                  (NEW)
src/datapulse/api/routes/__init__.py                             (modify — register router)
src/datapulse/pos/models/admin_release.py                        (NEW — pydantic models)
src/datapulse/pos/admin_release_service.py                       (NEW — DB ops)
tests/pos/test_admin_release_endpoint.py                         (NEW)
tests/pos/test_admin_release_service.py                          (NEW)
docs/ops/key-rotation.md                                         (modify — add CSC cert)
docs/ops/pos-desktop-update-verify.md                            (modify — drop migration step from §0)
```

Estimated: ~250 lines added, ~10 lines deleted, ~5 lines modified.

### Phase 1 (~80 files moved + ~15 new)

```
git mv frontend/src/app/(pos)/* → pos-desktop/src/pages/         (8 files)
git mv frontend/src/components/pos/* → pos-desktop/src/components/  (~25 files)
git mv frontend/src/hooks/use-pos-* → pos-desktop/src/hooks/     (~15 files)
git mv frontend/src/store/pos-cart-store.ts → pos-desktop/src/store/cart-store.ts
delete  frontend/src/contexts/pos-cart-context.tsx               (after unification)
NEW     pos-desktop/src/api/client.ts
NEW     pos-desktop/src/api/types.ts                             (generated)
NEW     pos-desktop/src/api/endpoints/transactions.ts            (and ~6 others)
NEW     pos-desktop/vite.config.ts
NEW     pos-desktop/index.html
modify  pos-desktop/electron/main.ts                             (loadFile instead of spawn)
modify  pos-desktop/electron-builder.yml                         (drop extraResources)
modify  pos-desktop/scripts/build.sh                             (drop Next.js copy block)
modify  frontend/src/app/globals.css                             (drop --pos-* tokens)
modify  frontend/src/app/layout.tsx                              (remove POS routes from sidebar nav, already done in #791)
modify  pos-desktop/package.json                                 (version 3.0.0)
NEW     pos-desktop/src/styles/globals.css                       (POS tokens only)
```

Estimated: ~1,200 lines moved, ~600 lines new, ~150 lines deleted.

## 10. Acceptance criteria

### Phase 2
- [ ] Workflow fails loudly if tag ≠ package.json version (verified by deliberate mismatch test)
- [ ] `POST /api/v1/pos/admin/desktop-releases` registers a rollout row, idempotent on re-call
- [ ] Workflow calls the endpoint after successful publish; release auto-registers
- [ ] Code-signing produces a Valid signature on the next release (verified by workflow's existing `Get-AuthenticodeSignature` step)
- [ ] No regression: a tag push end-to-end produces a published release + a registered DB row + a signed installer

### Phase 1
- [ ] All existing POS tests pass (unchanged behavior)
- [ ] Cashier walkthrough succeeds on staging (open shift → scan → checkout → close shift → receipt)
- [ ] `pos-desktop/dist/*-Setup.exe` is ~30% smaller than the current build (no embedded Node)
- [ ] Cart store has exactly one source of truth — `pos-desktop/src/store/cart-store.ts`
- [ ] `frontend/src/components/pos/`, `frontend/src/app/(pos)/`, `frontend/src/hooks/use-pos-*` directories no longer exist
- [ ] `frontend/src/app/globals.css` has no `--pos-*` tokens

### Phase 3
- [ ] 2 weeks of operation logged in metrics
- [ ] `docs/brain/decisions/2026-05-14-pos-extraction-outcome.md` written
- [ ] Either: this initiative is closed, or: a follow-on fork plan exists

## 11. Out-of-spec follow-ups (not this initiative)

- **Backend deploy reliability** — already covered by [PR #800](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/800). Separate.
- **Sentry alerting on prod outages** — top Phase-1 priority of the broader infra migration plan (see strategic discussion 2026-04-30).
- **Fork to separate repo** — explicitly deferred to Phase 3 outcome.
- **iOS/Linux desktop builds** — out of scope; Win32 only for now.
- **POS web access from browser** — drops in Phase 1 (becomes redirect to "open desktop app").

## 12. References

- Stuck-deploy incident: `docs/brain/incidents/2026-04-30-stuck-container-deploy-loop.md`
- POS visual port spec: `docs/superpowers/specs/2026-04-30-pos-terminal-visual-port-design.md`
- Update-policy design: `pos-desktop/electron/updater/index.ts` §2.4
- Update verification runbook: `docs/ops/pos-desktop-update-verify.md` (drafted, not yet pushed)
- Migration table: `migrations/115_pos_desktop_update_rollouts.sql`
- Today's bundled PRs: #795, #796, #797, #798, #799, #800, #801, #802
