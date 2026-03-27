# JerryScript on-device apps (unofficial)

Technical reference for AIs and users building **JavaScript** apps that run **on the BUSY Bar** (not Python widgets on the PC).

**Scope:** JerryScript / `js_runner` is **not** part of the **standard default** retail firmware line that users treat as “normal build.” This lesson lives under **[Unofficial/](README.md)** with other optional or experimental runtimes. Use it only when targeting firmware bundles that explicitly ship **JerryScript** and **js_runner**.

---

## 1. Relationship to HTTP widgets (Official 01–11)

- **Widgets** use **Python** (or any HTTP client) to call **`POST /api/display/draw`** with **DisplayElements** JSON. See **[../Official/09-Widget-template.md](../Official/09-Widget-template.md)**.
- **JerryScript apps** run **on the device** in the **js_runner** runtime. They use **`require("module")`** for native bindings. They do **not** use the draw JSON `elements` array unless the firmware exposes a bridge that does so (default mental model: **different API**).

If the user asks for a “widget,” assume **HTTP widget** unless they explicitly want **on-device JS**.

---

## 2. Prerequisites

- Firmware that includes **JerryScript** and **js_runner** (developer / experimental / custom bundles — not assumed on every stock device).
- Apps must be placed under **`/ext/apps/<app_id>/`** on device storage.

---

## 3. Minimal app layout

1. Create a folder: **`/ext/apps/<your_app_id>/`**
2. Add **`main.js`** (entry script).
3. Add **`app.json`** metadata:

```json
{
  "name": "My App",
  "runtime": "js",
  "entry": "main.js"
}
```

4. The app appears in the **Apps** menu when the device scans `/ext/apps`.

Optional menu icons: **`icon_front.bin`** and **`icon_back.bin`** next to `main.js` (if missing, placeholders may be used).

---

## 4. Native modules (overview)

Busy Bar exposes native modules via **`require("name")`**. The exact set can evolve with firmware; a typical set on JerryScript-enabled builds includes:

`device`, `display`, `input`, `power`, `storage`, `time`, `timer`, `status`, `audio`, `system`, `fs_extra`, `gui`, `fetch`, `json`, `settings`, `wifi`, `lottie`, `busy_timer`, `ble`, plus globals like **`str()`**, **`delay(ms)`**, **`print` / `console.log`**, and **`__runLoop()`** for event-driven apps (input/timer).

**Examples:**

- **display** — strip/back drawing; **text**, **pixel**, **rect**, **show**, etc.
- **fetch** — HTTP GET/POST; **json.parse** for JSON bodies.
- **storage** — persistent key/value or files (as implemented in firmware).
- **gui** — richer UI (LVGL-style) when available.
- **settings** — device settings.

For the authoritative, exhaustive API (every function and option), use the firmware **JerryScript App Development Guide** in the **bsb-fw-vibecode-context** / product documentation. This lesson is enough to **structure** apps correctly and avoid confusing them with widgets.

---

## 5. Deploying files (no firmware recompile for app-only changes)

Copy **`main.js`**, **`app.json`**, and assets into **`/ext/apps/<app_id>/`** using either:

- **HTTP storage API** — `POST /api/storage/mkdir`, `POST /api/storage/write`, etc. (see **[../Official/openapi.yaml](../Official/openapi.yaml)**; paths must be URL-encoded where required).
- **BUSY Bar Controller** — Device tab: storage or app upload flows, if available.

Updating an app’s **JS/assets** only does **not** require a firmware rebuild or reboot; behavior depends on how the launcher caches apps (usually pick up new files after restart of the app or device).

---

## 6. Reliability and edge cases

Apps should handle:

- **No Wi‑Fi** — show a clear message; do not assume `fetch` succeeds.
- **HTTP errors** — non-2xx, timeouts, redirects; validate before parsing JSON.
- **Partial data** — keep last good values or show a placeholder.

---

## 7. Mini UI SDK (optional)

Some projects use a **desktop helper** to design scene graphs (`project.json`) that mirror the **gui** contract. That workflow is separate from the HTTP widget pipeline; the SDK does not replace `require()` on device.

---

## 8. References

- **[../Official/03-Device-and-API.md](../Official/03-Device-and-API.md)** — connection and HTTP overview (including storage).
- **[../Official/openapi.yaml](../Official/openapi.yaml)** — full endpoint list.
- **[Custom-APPS-Lua/](Custom-APPS-Lua/)** — Lua-only legacy; do not mix `busy.*` APIs with JerryScript without checking firmware.
