# Safe Space Saturdays mobile release

## Local validation

```bash
npm install
npm run doctor
npm run typecheck
npm run export:android
npm run export:ios
```

The export commands validate the Android and iOS JavaScript bundles without requiring a simulator.

## Device testing

Install the Expo development build on a connected device or emulator:

```bash
npx expo run:android
npx expo run:ios
```

The Android command requires Android Studio, an SDK, and an emulator or USB device. The iOS command requires macOS, Xcode, and an iOS simulator or device. The Linux development host does not have either runtime installed, so those checks must be run in CI or on the respective platform.

Smoke-test these flows on both platforms:

1. Register, sign in, restart the app, and sign out.
2. Switch Sage, Night Garden, Tatty's Garden, and Crimson Ty in Profile; restart and confirm the selection persists.
3. Allow notifications and confirm the wellbeing reminder is scheduled.
4. Complete a check-in and verify the cooldown screen.
5. Upload a profile picture and attach a resized image to a community post.
6. Join a room, play Connect Four/Ludo, and verify turn updates.
7. Start Scribble, choose a word, draw with multiple colors, erase, clear, finish, and submit a guess.

## EAS builds

Create or select the Expo project, then configure the project ID in `app.json` under `expo.extra.eas.projectId`:

```bash
npx eas login
npx eas init
npm run build:preview
npm run build:production
npm run submit:production
```

Before the production build, replace the placeholder app-store identifiers and add Android keystore/iOS signing credentials through EAS. The API URL must be supplied as `EXPO_PUBLIC_API_URL` in the EAS environment.
