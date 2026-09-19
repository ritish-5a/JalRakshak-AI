# JalRakshak AI — PWA 100% Offline Testing & Verification Guide

This guide provides step-by-step instructions for testing the **100% Offline Resilience** of **JalRakshak AI** (SIH26071) using Browser Developer Tools (Chrome, Edge, Firefox, Safari) or physical mobile devices in **Airplane Mode**.

---

## 🏗️ PWA Architecture Overview

JalRakshak AI uses a multi-layered offline architecture to guarantee full operational resilience during catastrophic cloudbursts and cellular towers collapse:

1. **Service Worker Core (`service-worker.js`)**: Cache-First strategy for application shell (`index.html`, `styles.css`, `app.js`), Tailwind CDN, Google Fonts, and Leaflet map libraries.
2. **Tactical Vector SVG Tile Generator**: Automatically synthesizes OpenStreetMap vector SVG grid tiles when map tiles cannot be fetched over the network.
3. **Synthetic API Engine**: Intercepts `/api/` REST requests when offline and returns structured telemetry and prediction JSON fallbacks.
4. **On-Device Hydrological Engine**: Executes Soil Conservation Service Curve Number (SCS-CN) surface runoff calculations on client hardware.
5. **IndexedDB Telemetry & Queue (`JalRakshakCrextioDB`)**: Stores logs, sonar depth measurements, and queues emergency SOS alerts for automatic background sync when reconnected.

---

## 🧪 Method 1: Testing Offline Mode via Browser DevTools

### Step 1: Initial Load & Service Worker Verification
1. Open your browser (Google Chrome, Microsoft Edge, or Mozilla Firefox).
2. Open **JalRakshak AI** by navigating to `index.html` (or your local web server address `http://127.0.0.1:8000`).
3. Press `F12` (or `Ctrl+Shift+I` on Windows / `Cmd+Option+I` on macOS) to open **Developer Tools**.
4. Navigate to the **Application** tab (Chrome/Edge) or **Storage** tab (Firefox).
5. In the left sidebar, click **Service Workers**:
   - Confirm `service-worker.js` is registered and displays **Status: Activated and is running**.

### Step 2: Verify Cache Storage Population
1. Under the **Application** tab, expand **Cache Storage** in the left sidebar.
2. You should see three populated cache stores:
   - `jalrakshak-static-v2.0.0` (Contains `index.html`, `styles.css`, `app.js`, `manifest.json`, Tailwind CDN, Leaflet JS/CSS)
   - `jalrakshak-dynamic-v2.0.0` (Contains dynamic API fallbacks and Google Font binaries)
   - `jalrakshak-tiles-v2.0.0` (Contains cached map tile responses)

### Step 3: Simulate 100% Offline Network Disconnection
1. In DevTools, switch to the **Network** tab (or stay on the **Application > Service Workers** panel).
2. Locate the **Throttling** dropdown menu (which defaults to `No throttling` or `Online`).
3. Select **Offline**.
4. Alternatively, check the **Offline** checkbox directly under **Application > Service Workers**.

### Step 4: Refresh & Test App Shell
1. Press `F5` or `Ctrl+R` (`Cmd+R` on macOS) to hard refresh the page.
2. **Result**: The JalRakshak AI dashboard reloads **instantly with 0 network requests**, powered completely by the Service Worker Cache Storage.
3. Observe the green/red status indicator dot next to the search bar — it pulses red to indicate **100% PWA Offline Mode Active**.

---

## 📱 Method 2: Testing Offline Mode via Mobile Device & Airplane Mode

### Step 1: Install PWA on Device
1. Open JalRakshak AI in Chrome (Android) or Safari (iOS).
2. Tap the browser menu option **"Add to Home Screen"** or **"Install App"**.
3. Confirm installation. A JalRakshak AI icon will appear on your mobile home screen.

### Step 2: Enable Airplane Mode
1. Swipe down the notification tray / Control Center on your phone.
2. Enable **Airplane Mode** (ensure Wi-Fi, Mobile Data, and Cellular radios are completely turned OFF).

### Step 3: Launch Standalone App Offline
1. Tap the **JalRakshak AI** icon on your home screen.
2. The application will launch full-screen as a native standalone PWA app without network connectivity.

---

## ✅ Feature-by-Feature Offline Verification Matrix

| Feature / Module | How to Test Offline | Expected Behavior |
| :--- | :--- | :--- |
| **App Shell & UI** | Reload page with Network set to `Offline`. | Dashboard, Tailwind layout, buttons, icons, fonts render seamlessly without layout shifts. |
| **Leaflet GIS Map** | Pan and zoom into Karnataka districts. | OpenStreetMap tiles serve from cache. Uncached tiles display tactical SVG vector radar grid tiles (`TILE: Z/X/Y`). |
| **Sonic Hydro-Depth Scanner** | Click `EMIT 14kHz ACOUSTIC CHIRP PULSE`. | Emits 14kHz Web Audio tone, computes echo timing in milliseconds, displays flood depth in mm, updates canvas spectrum, and logs to IndexedDB. |
| **On-Device Geocoding & Search** | Type "Bengaluru" or "Victoria" in top search bar. | Instant offline suggestions dropdown appears. Clicking an item centers map and drops search pin. |
| **SCS-CN Hydro Runoff Engine** | Change Rain Rate / Duration in Hydro Engine section and click `COMPUTE RUNOFF`. | Executes client-side SCS-CN math formula, calculates runoff volume (m³), peak discharge (m³/s), surface flood depth, and updates hazard rating. |
| **Manual SMS SOS Dispatch** | Click `MANUAL DISPATCH SOS (SMS)` button. | Generates GSM `sms:` URI, opens native device SMS app with emergency coordinates, logs to IndexedDB, and queues action for background sync. |
| **NDMA Emergency PDF Report** | Click `Export NDMA PDF` button. | Opens NDMA compliance modal. Clicking `PRINT / SAVE PDF` opens browser print preview offline. |
| **PWA System Inspector** | Click system status dot button (top right). | Queries Service Worker via `MessageChannel` and displays cache stats and network telemetry toast. |

---

## 🔍 Inspecting Offline Storage & Sync Queue in DevTools

### Viewing IndexedDB Logs:
1. Open DevTools (`F12`) -> **Application** tab.
2. Expand **IndexedDB** -> `JalRakshakCrextioDB`.
3. Inspect object stores:
   - `logs`: Stores acoustic sonar depth scans and manual SOS dispatches with timestamps.
   - `offline_queue`: Stores pending API requests queued during offline mode.

### Testing Automatic Background Sync:
1. While in **Offline** mode, click `MANUAL DISPATCH SOS (SMS)`. Notice an entry added to `offline_queue` in IndexedDB.
2. Switch network throttling back to **Online**.
3. The Service Worker listens to the `online` event and `sync` tag, automatically processing the queued requests and clearing `offline_queue`.

---

## 🛠️ Summary

With this PWA architecture, JalRakshak AI ensures **zero downtime and 100% operational resilience** during extreme weather disasters. All critical early warning workflows function completely offline.
