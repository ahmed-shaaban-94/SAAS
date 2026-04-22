# Auth0 Action — surface `locale` claim (#604)

## Why

`get_current_user` reads an optional `locale` claim and surfaces it on
`UserClaims`. The frontend uses it as the default when a user hasn't
picked a locale via the UI switcher yet. Auth0 does not ship this claim
by default — deploy the action below once per tenant in the Auth0
dashboard.

## The action

1. Auth0 Dashboard → Actions → Library → Build Custom → name it
   `surface-locale-claim`, flow: `Login / Post Login`.
2. Paste this code:

```js
exports.onExecutePostLogin = async (event, api) => {
  const locale = event.user.user_metadata?.locale || event.request.locale;
  if (locale) {
    api.idToken.setCustomClaim("locale", locale);
    api.accessToken.setCustomClaim("locale", locale);
  }
};
```

3. Deploy, then drag it into the `Login` flow.
4. Verify: log in as a test user, inspect the JWT payload — `locale`
   should appear as a top-level claim.

## Fallback behavior

If the action is **not** deployed, every user gets `locale = "en-US"`
on the backend. No crash — users can still override via the in-app
locale switcher.
