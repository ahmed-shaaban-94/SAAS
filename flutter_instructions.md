# Flutter Setup & Run Instructions

## 1. Install Flutter SDK

Flutter was downloaded and extracted to `C:\flutter`.

If you need to reinstall:
1. Download from: https://flutter.dev/docs/get-started/install/windows
2. Extract zip to `C:\flutter`
3. Add `C:\flutter\bin` to your PATH environment variable:
   ```powershell
   [Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';C:\flutter\bin', 'User')
   ```
4. Reopen PowerShell

---

## 2. Upgrade Flutter

After installing, upgrade to the latest stable version:

```powershell
flutter upgrade
```

---

## 3. Accept Android Licenses

```powershell
flutter doctor --android-licenses
```

Press `y` for each license prompt.

---

## 4. Check Setup

```powershell
flutter doctor
```

Expected output:
- Windows Version: OK
- Android toolchain: OK (may show SDK version warning — ignore if SDK >= 36)
- Chrome: OK
- Visual Studio: OK
- Connected device: OK

---

## 5. Install App Dependencies

```powershell
cd "C:\Users\Shaaban\Documents\GitHub\Data-Pulse\flutter_app"
flutter pub get
```

---

## 6. Run the App

### Option A — Android Emulator (recommended)
1. Open **Android Studio**
2. Click **Device Manager** (right sidebar)
3. Click **Play ▶** next to any AVD (e.g. Pixel 9)
4. Wait for emulator to fully boot
5. Run:
   ```powershell
   flutter run
   ```

### Option B — Chrome (quickest, no emulator needed)
```powershell
flutter run -d chrome
```

---

## 7. Auth0 Configuration

The app is configured with:
- **API URL**: `https://smartdatapulse.tech`
- **Auth0 Domain**: `datapulse.eu.auth0.com`
- **Client ID**: `P30k0QvXgyS7fwFT7nwc703WvS7XKZBV` (Flutter Native app)

These are set in `flutter_app/lib/config/constants.dart`.

### Auth0 Dashboard Settings (already configured)
- **Allowed Callback URLs**: `com.datapulse.app://datapulse.eu.auth0.com/android/com.datapulse.app/callback`
- **Allowed Logout URLs**: same as above

### Android build.gradle (add when Android folder is generated)
Inside `android/app/build.gradle` under `defaultConfig`:
```gradle
manifestPlaceholders += [auth0Domain: "datapulse.eu.auth0.com", auth0Scheme: "com.datapulse.app"]
```

---

## 8. Notes

- Flutter SDK is separate from Android SDK — Flutter uses Android SDK under the hood
- Android SDK (API 37) is installed via Android Studio
- The Flutter app connects to the production API on the droplet (164.92.243.3)
- The droplet runs API, PostgreSQL, dbt, n8n — Flutter just calls it over HTTPS
