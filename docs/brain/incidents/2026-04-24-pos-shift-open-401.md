---
date: 2026-04-24
severity: alpha-blocker
area: pos-desktop / auth
related_prs: [668, 690, 692]
smoke_build: pos-smoke-build-v7
---

# POS desktop: `401 Authentication required` on shift-open

## Symptom

Packaged POS installer (`pos-smoke-build-v7`, installed to
`C:\Program Files\DataPulse POS`) opens to `/terminal`. Because there is no
active terminal session, the `ShiftOpenModal` is rendered. Entering an opening
balance (`1000 EGP`) and clicking **فتح الوردية** produces a red error banner:

```
API error 401: {"detail":"Authentication required"}
```

The error comes straight from the backend (`src/datapulse/core/auth.py:236-239`,
the terminal branch of `get_current_user` that fires only when **no**
credential mechanism — Bearer, X-API-Key, or dev fallback — is present).

## Root cause

The POS desktop renders the shift-open modal to **anonymous** users. The
backend correctly rejects the subsequent `POST /api/v1/pos/terminals` because
no `Authorization: Bearer <jwt>` header is attached.

Four cooperating factors:

1. **#692 (`POS_DESKTOP_MODE=1`)** — the embedded Next.js server skips the
   server-side auth middleware on purpose, because baking `CLERK_SECRET_KEY`
   into the distributable installer would leak it to every pilot machine.
   The design intent, stated in `main.ts` and the PR body, was that
   "browser-side Clerk components handle session display using the public
   key." That browser-side gate was never actually wired up.
2. **`SessionGuard` is a non-gate.** `frontend/src/app/(pos)/layout.tsx:45-63`
   blocks rendering only while `status === "loading"`. When Clerk finishes
   initialising as `"unauthenticated"`, the guard falls through and renders
   children — including the shift-open modal.
3. **`api-client.ts` silently omits auth.** `getAuthHeaders()` returns `{}`
   when `getSession()` yields null (anonymous user). The request goes out
   without an `Authorization` header, so the backend's `get_current_user`
   takes the final `raise HTTPException(401, "Authentication required")` path.
4. **Electron entrypoint loads `/terminal` directly.** `main.ts:235`
   (`mainWindow.loadURL(".../terminal")`) skips any sign-in landing page.
   There is no `/sign-in` → `/terminal` redirect in `POS_ROUTES` either.

Today's PRs that interacted with this area but did **not** introduce the bug
(they only exposed it by unblocking earlier failure modes):

| PR | Effect |
|----|--------|
| #668 | Removed Auth0, made Clerk the sole IdP. |
| #681 | Provided `NEXTAUTH_SECRET` so the embedded server can boot. |
| #687 | Stopped readiness probe hanging on dead NextAuth route. |
| #689 | Stopped pino worker double-init crash in main process. |
| #690 | Wired Clerk publishable key into the build. Verified baked into v7 (`pk_test_b3JpZW50ZWQtbGFyay02OC5jbGVyay5hY2NvdW50cy5kZXYk`). |
| #692 | `POS_DESKTOP_MODE=1` — skipped server-side middleware. |
| #694 | OTel tracing. Unrelated. |
| #695 | POS-desktop CORS origin + headers. Unrelated (headers are server-emitted; auth failure is pre-CORS). |

## Fix

Minimal, surgical, two files — no new abstractions, no backend change.

### 1. `frontend/src/app/(pos)/layout.tsx` — make `SessionGuard` an actual gate

Treat `"unauthenticated"` as blocking: redirect to sign-in with
`callbackUrl: "/terminal"` and show the loading spinner until Clerk confirms
an authenticated session. Only then render children.

### 2. `pos-desktop/electron/main.ts` — allow Clerk routes in `POS_ROUTES`

The `did-navigate` handler in `main.ts` bounces any hostname=localhost path
that isn't in `POS_ROUTES` back to `/terminal`. Added `/sign-in` and
`/sign-up` (Clerk's catch-all `[[...sign-in]]` routes) so the SessionGuard
redirect doesn't loop.

## Verification

- Publishable key confirmed baked into the v7 installer:
  `grep -roE "pk_(test|live)_[A-Za-z0-9]{20,}" "C:/Program Files/DataPulse POS/resources"`
  → `pk_test_b3JpZW50ZWQtbGFyay02OC5jbGVyay5hY2NvdW50cy5kZXYk` (dev key).
- `tsc --noEmit` clean on both touched files.
- Existing `__tests__/app/(pos)/*.test.tsx` render the page directly without
  the layout, so they don't exercise `SessionGuard` and aren't affected.
- **Not yet verified on the installed artifact.** The existing v7 installer
  cannot pick up this fix without a rebuild. The smoke test should be re-run
  after the next CI build.

## Prevention

- **Add a unit test** for `SessionGuard` that asserts `signIn()` is called
  when `status === "unauthenticated"` and that children are NOT rendered.
  (Out of scope for this incident fix — a follow-up PR.)
- **Long term:** consider migrating the POS layout to Clerk's
  `<SignedIn>` / `<SignedOut>` / `<RedirectToSignIn>` components directly
  rather than going through the `auth-bridge` shim — the bridge still carries
  Auth0 return-path machinery that is dead post-#668 (tracked in #682).
