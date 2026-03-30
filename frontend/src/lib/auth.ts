import type { AuthOptions } from "next-auth";
import type { JWT } from "next-auth/jwt";
import KeycloakProvider from "next-auth/providers/keycloak";

/**
 * Refresh the Keycloak access token using the refresh_token grant.
 * Returns the updated JWT on success, or marks it with an error on failure.
 */
async function refreshAccessToken(token: JWT): Promise<JWT> {
  const issuer = process.env.KEYCLOAK_ISSUER!;
  const tokenUrl = `${issuer}/protocol/openid-connect/token`;

  try {
    const params = new URLSearchParams({
      client_id: process.env.KEYCLOAK_CLIENT_ID!,
      grant_type: "refresh_token",
      refresh_token: token.refreshToken as string,
    });

    // For confidential clients, include the secret
    if (process.env.KEYCLOAK_CLIENT_SECRET) {
      params.set("client_secret", process.env.KEYCLOAK_CLIENT_SECRET);
    }

    const res = await fetch(tokenUrl, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: params.toString(),
    });

    const refreshed = await res.json();

    if (!res.ok) {
      throw new Error(refreshed.error_description || "Token refresh failed");
    }

    return {
      ...token,
      accessToken: refreshed.access_token,
      refreshToken: refreshed.refresh_token ?? token.refreshToken,
      expiresAt: Math.floor(Date.now() / 1000) + refreshed.expires_in,
      error: undefined,
    };
  } catch {
    return { ...token, error: "RefreshAccessTokenError" };
  }
}

/**
 * Decode a JWT payload without verification (claims extraction only).
 */
function decodeJwtPayload(token: string): Record<string, unknown> {
  try {
    const base64 = token.split(".")[1];
    const json = Buffer.from(base64, "base64").toString("utf-8");
    return JSON.parse(json);
  } catch {
    return {};
  }
}

export const authOptions: AuthOptions = {
  providers: [
    KeycloakProvider({
      clientId: process.env.KEYCLOAK_CLIENT_ID || "datapulse-frontend",
      clientSecret: process.env.KEYCLOAK_CLIENT_SECRET || "",
      issuer: process.env.KEYCLOAK_ISSUER || "http://localhost:8080/realms/datapulse",
    }),
  ],

  pages: {
    signIn: "/login",
  },

  session: {
    strategy: "jwt",
    maxAge: 24 * 60 * 60, // 24 hours
  },

  callbacks: {
    async jwt({ token, account }) {
      // On initial sign-in, persist the tokens from the OAuth provider
      if (account) {
        const claims = decodeJwtPayload(account.access_token as string);

        // Extract tenant_id — Keycloak can put this in a custom claim or realm_access
        const tenantId =
          (claims.tenant_id as number) ??
          (claims.tenantId as number) ??
          undefined;

        // Extract realm roles
        const realmAccess = claims.realm_access as
          | { roles?: string[] }
          | undefined;
        const roles = realmAccess?.roles ?? [];

        return {
          ...token,
          accessToken: account.access_token as string,
          refreshToken: account.refresh_token as string,
          expiresAt: account.expires_at as number,
          tenant_id: tenantId,
          roles,
        };
      }

      // If the token hasn't expired yet, return it as-is
      if (token.expiresAt && Date.now() / 1000 < token.expiresAt - 60) {
        return token;
      }

      // Token is expired or about to expire — refresh it
      return refreshAccessToken(token);
    },

    async session({ session, token }) {
      session.accessToken = token.accessToken;
      session.error = token.error;

      if (session.user) {
        session.user.tenant_id = token.tenant_id;
        session.user.roles = token.roles;
      }

      return session;
    },
  },
};
