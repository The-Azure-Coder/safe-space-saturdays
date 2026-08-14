# Safe Space Saturdays mobile app

This is the Expo React Native client for Safe Space Saturdays. It uses the existing FastAPI API, bearer session tokens, and the same PostgreSQL/Redis-backed multiplayer services as the web app.

## Start

```bash
cp .env.example .env
npm install
npx expo start
```

For a physical device, set `EXPO_PUBLIC_API_URL` to the API's LAN address instead of `localhost`.

The first slice includes session restore, login, registration, a tabbed home shell, games/community/profile entry points, and the shared theme foundation. Game screens and the full API-backed content flows will be added on top of this authenticated shell.
