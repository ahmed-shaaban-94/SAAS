import type { AuthOptions } from "next-auth";
import type { JWT } from "next-auth/jwt";

// Auth0 configuration
const AUTH0_DOMAIN = process.env.AUTH0_DOMAIN || "";
const AUTH0_ISSUER = `https://${AUTH0_DOMAIN}`;

/**
 * Refresh the Auth0 access token using the refresh_token grant.
 * Returns the updated JWT on success, or marks it with an error on failure.
 */
async function refreshAccessToken(token: JWT): Promise<JWT> {
  const tokenUrl = `${AUTH0_ISSUER}/oauth/token`;

  try {
    const params = new URLSearchParams({
      client_id: process.env.AUTH0_CLIENT_ID!,
      grant_type: "refresh_token",
      refresh_token: token.refreshToken as string,
    });

    if (process.env.AUTH0_CLIENT_SECRET) {
      params.set("client_secret", process.env.AUTH0_CLIENT_SECRET);
    }

    const res = await fetch(tokenUrl, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: params.toString(),
    });

    const refreshed = await res.json();

    if (!res.ok) {
      console.error("[TOKEN_REFRESH] Failed:", refreshed.error, refreshed.error_description);
      throw new Error(refreshed.error_description || "Token refresh failed");
    }

    const refreshedToken: JWT = {
      ...token,
      accessToken: refreshed.access_token,
      refreshToken: refreshed.refresh_token ?? token.refreshToken,
      expiresAt: Math.floor(Date.now() / 1000) + refreshed.expires_in,
    };
    delete refreshedToken.error;
    return refreshedToken;
  } catch (err) {
    console.error("[TOKEN_REFRESH] Exception:", err);
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

const auth0Provider: any = {
  id: "auth0",
  name: "Auth0",
  type: "oauth",
  clientId: process.env.AUTH0_CLIENT_ID || "",
  clientSecret: process.env.AUTH0_CLIENT_SECRET || "",
  wellKnown: `${AUTH0_ISSUER}/.well-known/openid-configuration`,
  authorization: {
    params: {
      scope: "openid email profile offline_access",
      audience: process.env.AUTH0_AUDIENCE || "",
    },
  },
  idToken: true,
  checks: ["pkce", "state"],
  profile(profile: any) {
    return {
      id: profile.sub,
      name: profile.name ?? profile.nickname,
      email: profile.email,
      image: profile.picture,
    };
  },
};

export const authOptions: AuthOptions = {
  providers: [auth0Provider],
  debug: process.env.NODE_ENV === "development",

  logger: {
    error(code, metadata) {
      console.error("[NEXTAUTH_ERROR]", code, JSON.stringify(metadata, null, 2));
    },
    warn(code) {
      console.warn("[NEXTAUTH_WARN]", code);
    },
    debug(code, metadata) {
      console.log("[NEXTAUTH_DEBUG]", code, JSON.stringify(metadata, null, 2));
    },
  },

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

        // Extract tenant_id from Auth0 custom claim (set via Auth0 Action/Rule)
        const tenantId =
          (claims["https://datapulse.tech/tenant_id"] as number) ??
          (claims.tenant_id as number) ??
          undefined;

        // Extract roles from Auth0 namespaced claim or permissions
        const roles =
          (claims["https://datapulse.tech/roles"] as string[]) ??
          (claims.permissions as string[]) ??
          [];

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
