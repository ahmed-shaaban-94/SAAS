/**
 * Auth0 Post-Login Action — Injects tenant_id into access tokens.
 *
 * Setup:
 *   1. Auth0 Dashboard -> Actions -> Library -> "Build Custom"
 *   2. Name: "Add Tenant Claims"
 *   3. Trigger: Login / Post Login
 *   4. Paste this code -> Deploy
 *   5. Actions -> Flows -> Login -> Drag "Add Tenant Claims" into the flow
 *
 * For single-tenant deployments, this hardcodes tenant_id = "1".
 * For multi-tenant, store tenant_id in user app_metadata via the Auth0
 * Management API or during registration.
 */
exports.onExecutePostLogin = async (event, api) => {
  const namespace = "https://datapulse.tech";

  // Single-tenant: always "1".  Multi-tenant: read from app_metadata.
  const tenantId = event.user.app_metadata?.tenant_id || "1";

  api.accessToken.setCustomClaim(`${namespace}/tenant_id`, tenantId);
  api.accessToken.setCustomClaim(
    `${namespace}/roles`,
    event.authorization?.roles || []
  );
};
