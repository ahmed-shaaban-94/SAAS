/**
 * Playwright Global Setup — CI Auth Session
 *
 * Runs once before all tests. In CI, mints a valid NextAuth v4 JWT session
 * cookie (signed with NEXTAUTH_SECRET) and saves it to e2e/.auth/user.json so
 * that every test fixture starts as an authenticated user.
 *
 * Token fields mirror what the real jwt() callback stores on first sign-in
 * (auth.ts lines 134-141). Crucially, `expiresAt` must be set far in the
 * future so the jwt() callback takes the early-return branch and never calls
 * refreshAccessToken() — which would otherwise try to reach the Auth0 token
 * endpoint and fail with EAI_AGAIN in the offline CI environment.
 *
 * Tests that specifically need an *unauthenticated* context (auth.spec.ts)
 * already create their own browser context with `storageState: undefined`,
 * which overrides this global state.
 */

import fs from "fs";
import path from "path";
import { chromium, FullConfig } from "@playwright/test";
import { encode } from "next-auth/jwt";

const AUTH_STATE_PATH = path.join(__dirname, ".auth", "user.json");

async function globalSetup(_config: FullConfig): Promise<void> {
  // Only create the session in CI — local dev authenticates via real Auth0 flow.
  if (!process.env.CI) return;

  const secret =
    process.env.NEXTAUTH_SECRET ?? "ci-e2e-placeholder-not-for-production";

  const nowSec = Math.floor(Date.now() / 1000);
  const ttl = 60 * 60 * 24; // 24 hours

  // Mint a valid NextAuth JWT using the same encoder the framework uses.
  // `expiresAt` (Auth0 access-token expiry) prevents refreshAccessToken() from
  // being invoked — without it the jwt() callback always attempts a token
  // refresh that fails in CI (no Auth0 reachable).
  const sessionToken = await encode({
    token: {
      sub: "auth0|ci-test-user-001",
      name: "CI Test User",
      email: "ci@datapulse.io",
      picture: null,
      tenant_id: "1",
      roles: ["admin"],
      // Match the shape written by the real jwt() callback on first sign-in:
      accessToken: "ci-dummy-access-token",
      refreshToken: "ci-dummy-refresh-token",
      expiresAt: nowSec + ttl, // ← key: keeps jwt() in the fast-return branch
      iat: nowSec,
      exp: nowSec + ttl,
    },
    secret,
    maxAge: ttl,
  });

  // Inject the token as a cookie and persist the browser storage state.
  fs.mkdirSync(path.dirname(AUTH_STATE_PATH), { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext();

  await context.addCookies([
    {
      name: "next-auth.session-token",
      value: sessionToken,
      domain: "localhost",
      path: "/",
      httpOnly: true,
      secure: false,
      sameSite: "Lax",
    },
  ]);

  await context.storageState({ path: AUTH_STATE_PATH });
  await browser.close();
}

export default globalSetup;
