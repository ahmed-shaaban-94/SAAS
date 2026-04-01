/**
 * TEMPORARY DEV-ONLY LOGIN ROUTE
 * Creates a NextAuth session for demo-admin without going through Auth0 browser flow.
 * Gets a real Auth0 access token via Resource Owner Password grant (if configured).
 * DELETE THIS FILE after auth testing is complete.
 */
import { encode } from "next-auth/jwt";
import { NextResponse } from "next/server";

export async function GET() {
  if (process.env.NODE_ENV !== "development") {
    return NextResponse.json({ error: "dev only" }, { status: 403 });
  }

  const secret = process.env.NEXTAUTH_SECRET!;
  const auth0Domain = process.env.AUTH0_DOMAIN || "";

  // --- Get a real Auth0 access token via Resource Owner Password grant ---
  let accessToken = "dev-access-token";
  let refreshToken = "dev-refresh-token";
  let expiresAt = Math.floor(Date.now() / 1000) + 3600;

  if (auth0Domain) {
    try {
      const tokenUrl = `https://${auth0Domain}/oauth/token`;
      const res = await fetch(tokenUrl, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          client_id: process.env.AUTH0_CLIENT_ID || "",
          client_secret: process.env.AUTH0_CLIENT_SECRET || "",
          grant_type: "password",
          username: process.env.DEV_LOGIN_USERNAME || "demo-admin",
          password: process.env.DEV_LOGIN_PASSWORD || "",
          audience: process.env.AUTH0_AUDIENCE || "",
          scope: "openid email profile offline_access",
        }).toString(),
      });

      if (res.ok) {
        const tokens = await res.json();
        accessToken = tokens.access_token ?? accessToken;
        refreshToken = tokens.refresh_token ?? refreshToken;
        expiresAt = Math.floor(Date.now() / 1000) + (tokens.expires_in ?? 3600);
      } else {
        console.warn("[dev-login] Auth0 token fetch failed, using fake token");
      }
    } catch (err) {
      console.warn("[dev-login] Auth0 token fetch error:", err);
    }
  }

  // Build a NextAuth JWT payload for demo-admin
  const token = await encode({
    token: {
      name: "Demo Admin",
      email: "admin@datapulse.dev",
      picture: undefined,
      sub: "demo-admin-sub",
      accessToken,
      refreshToken,
      expiresAt,
      tenant_id: 1,
      roles: ["admin"],
    },
    secret,
    maxAge: 24 * 60 * 60,
  });

  const response = NextResponse.redirect(
    new URL("/dashboard", "http://localhost:3000"),
  );

  // Set the NextAuth session cookie
  response.cookies.set("next-auth.session-token", token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 24 * 60 * 60,
  });

  return response;
}
