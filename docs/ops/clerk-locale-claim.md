# Clerk — surface `locale` claim via JWT template (#604)

## Why

DataPulse's `get_current_user` reads an optional `locale` top-level claim
from every verified JWT. The frontend uses it as the default when a user
hasn't picked a locale via the in-app switcher yet. Clerk does not include
`locale` by default — add a JWT template to surface it.

## One-time setup

1. Clerk Dashboard → your application → **JWT Templates** → *New template*.
2. Name it `datapulse` (the template name must match the audience your API
   expects; mirror whatever the existing templates use).
3. In the "Claims" JSON editor, ensure the custom claims include:
   ```json
   {
     "tenant_id": "{{user.public_metadata.tenant_id}}",
     "locale":    "{{user.public_metadata.locale}}",
     "roles":     "{{user.public_metadata.roles}}"
   }
   ```
4. On each user's profile, set `publicMetadata.locale` to the BCP-47 code
   (e.g. `"ar-EG"` or `"en-US"`). This can be automated via Clerk's
   pre-signup webhook or admin API.
5. Save + deploy.

## Fallback behavior

If `publicMetadata.locale` is unset, Clerk sends `null` for the claim and
`get_current_user` falls through to `"en-US"` by default. No crash.

## Swap between providers

`AUTH_PROVIDER=auth0` vs `AUTH_PROVIDER=clerk` in `.env` decides which
provider's JWTs are verified. Both providers' `locale` pipelines are
independent — deploying one does not require touching the other. Either
one can be fully omitted and `locale` will simply default to `en-US`
for that provider's users.

See also: `docs/ops/auth0-locale-action.md` for the Auth0 equivalent.
