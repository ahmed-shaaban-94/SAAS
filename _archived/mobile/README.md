# DataPulse Mobile

Expo + React Native starter for the mobile version of DataPulse.

## Why this exists

This app is the forward mobile path for the project. The goal is:

- `frontend/` stays the web app
- `mobile/` becomes the mobile app
- backend contracts and business logic get shared deliberately
- Flutter is not the forward delivery path

## Quick start

```bash
cd mobile
copy .env.example .env.local
npm install
npm run start
```

Then launch on:

- Android emulator: `npm run android`
- iOS simulator: `npm run ios`
- Expo web preview: `npm run web`

## Environment

Expo only exposes variables prefixed with `EXPO_PUBLIC_`.

Use:

- `EXPO_PUBLIC_API_URL`
- `EXPO_PUBLIC_API_KEY` for local development only

Example values:

```env
EXPO_PUBLIC_API_URL=http://10.0.2.2:8000
EXPO_PUBLIC_API_KEY=
```

Notes:

- Android emulator usually reaches the host machine via `10.0.2.2`
- iOS simulator usually reaches the host machine via `http://localhost:8000`
- a physical device needs your machine's LAN IP, for example `http://192.168.1.50:8000`

## Current foundation

- typed API client for readiness + dashboard summary
- starter mobile dashboard screen
- pull-to-refresh flow
- repo-ready folder structure for future navigation/auth/contracts work

## Recommended next steps

1. Add the canonical auth flow used by the web app.
2. Generate shared TypeScript API contracts from FastAPI.
3. Port the upload, dashboard, alerts, and reporting flows.
4. Add React Navigation or Expo Router after the screen map is agreed.
