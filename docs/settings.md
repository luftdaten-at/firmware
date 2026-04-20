# Configuration reference (`settings.toml` & `boot.toml`)

Persistent configuration lives on the device as TOML files on the CircuitPython filesystem (typically the CIRCUITPY root). The firmware loads them through [`Config`](../firmware/config.py) and [`AutoSaveDict`](../firmware/config.py): each known key is mapped to exactly one file (`settings.toml` or `boot.toml`). When code assigns `Config.settings[key] = value`, the value is written back to the mapped file.

**Source of truth for which key lives in which file:** `Config.key_to_toml_file` in [`firmware/config.py`](../firmware/config.py).

**Runtime-only values** (not stored in TOML) live in `Config.runtime_settings` (for example `API_URL` after `Config.set_api_url()`, RTC flags, update paths). They are summarized at the end of this document.

Sample / template files in the repo:

- [`firmware/settings.toml`](../firmware/settings.toml)
- [`firmware/boot.toml`](../firmware/boot.toml)

---

## `boot.toml`

Shipped with the firmware image. Intended for **product-wide** defaults: URLs, firmware version fields, manufacture suffix, TLS bundle path. The application does not treat these as “per-device” secrets; they still flow through `Config.settings` so one code path can read version and endpoints.

| Key | Type | Description |
|-----|------|-------------|
| `FIRMWARE_MAJOR` | integer | Major version (BLE, APIs, logs). |
| `FIRMWARE_MINOR` | integer | Minor version. |
| `FIRMWARE_PATCH` | integer | Patch version. |
| `PROTOCOL_VERSION` | integer | BLE / protocol version exposed to apps. |
| `MANUFACTURE_ID` | string | Suffix appended when generating `device_id` from MAC: `{mac}{MANUFACTURE_ID}`. |
| `API_URL` | string | Production **station** API base (Air Station Wi‑Fi: measurements use `runtime_settings['API_URL']` derived from this when not in test mode). |
| `TEST_API_URL` | string | Staging **station** API base (used when `TEST_MODE` is true for Air Station Wi‑Fi). |
| `UPDATE_SERVER` | string | OTA / upgrade metadata base URL (production). |
| `TEST_UPDATE_SERVER` | string | OTA base URL when `TEST_MODE` is true. |
| `DATAHUB_API_URL` | string | Datahub API root (e.g. `…/api/v1/devices`) for production. |
| `DATAHUB_TEST_API_URL` | string | Datahub root for staging when `TEST_MODE` is true. |
| `CERTIFICATE_PATH` | string | Path on device to the PEM used to verify HTTPS for the main API session (default `certs/isrgrootx1.pem`). |

---

## `settings.toml`

Per-device and user-facing options: Wi‑Fi, model, keys, Air Station behaviour, etc.

| Key | Type | Description |
|-----|------|-------------|
| `MODEL` | integer | Product type. Must match [`LdProduct`](../firmware/enums.py) (see table below). `-1` can be used with sensor-based detection flows (see [`startup.toml`](../firmware/startup.toml) `DETECT_MODEL_FROM_SENSORS`). |
| `boot_into` | any | Reserved / optional boot routing key in config map; not referenced elsewhere in the main firmware tree. Safe to leave unset. |
| `mac` | string / null | Wi‑Fi interface MAC (hex, uppercase). If `null` on first boot, firmware fills it from the radio and persists it. |
| `api_key` | string / null | Device API key for backends. If `null`, firmware generates a random key and saves it. |
| `device_id` | string / null | Public device identifier. If `null`, set to `{mac}{MANUFACTURE_ID}` during `Config.init()`. |
| `SSID` | string | Wi‑Fi network name (empty if unused). |
| `PASSWORD` | string | Wi‑Fi pre-shared key. If empty, firmware may use **enterprise** credentials below when all three are set. |
| `TEST_MODE` | boolean | If true: staging station URL, staging datahub, staging update server, and related test endpoints. |
| `CALIBRATION_MODE` | boolean / null | Calibration flag from settings or API. If `null`, runtime calibration is inferred when `SSID == "luftdaten.at"`. |
| `SEND_TO_SENSOR_COMMUNITY` | boolean | When true (Air Station path), also push to Sensor.Community in addition to other telemetry. |
| `LOG_LEVEL` | string | Minimum log level for [`SimpleLogger`](../firmware/logger.py): `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (case-insensitive). Messages below this are not printed or added to `logger.log_list`. Default **`DEBUG`**. Unknown values are treated like **`DEBUG`**. |
| `longitude` | string | Air Station / location: longitude (string in settings; APIs normalize to float or null). |
| `latitude` | string | Air Station / location: latitude. |
| `height` | string | Air Station / location: height above sea level. |
| `auto_update_mode` | integer | [`AutoUpdateMode`](../firmware/enums.py): `off = 0`, `critical = 2`, `on = 3`. Writable over BLE on Air Station. |
| `battery_save_mode` | integer | [`BatterySaverMode`](../firmware/enums.py): `off = 0`, `normal = 1`, `ultra = 3`. |
| `measurement_interval` | integer | Seconds between measurements. Use values from [`AirStationMeasurementInterval`](../firmware/enums.py) (e.g. `30`, `60`, `180`, …). |
| `SCL` | integer / null | Optional I²C SCL pin override (board default used if `null`). |
| `SDA` | integer / null | Optional I²C SDA pin override. |
| `BUTTON_PIN` | integer / null | Optional user button GPIO override. |
| `WIFILESS_MODE` | boolean / string | **Air Station only:** if true, skip normal Wi‑Fi/API loop and log measurements to SD (see [`readme.md`](../firmware/readme.md)). String values `1` / `true` / `yes` (case-insensitive) are accepted. |
| `SD_LOG_PATH` | string | **Air Station wifiless:** JSONL log path (default `/sd/measurements.jsonl`). |
| `ROLLBACK` | boolean | Set by the upgrade path / `code.py` to force booting the previous firmware bundle after a failed update. |
| `TZ` | string | Time zone for **API / log string** timestamps only (`format_iso8601_tz`). **Default:** `Europe/Vienna` if unset or empty. Recognised values: `UTC` / `GMT` / `Etc/UTC` / `Zulu` (case-insensitive) → suffix `Z`; `Europe/Vienna` → EU DST, suffix `+01:00` / `+02:00` (Datahub and related backends accept these numeric offsets, not only `Z`). The **RTC** after Wi‑Fi NTP is always set to **UTC** wall fields ([`WifiUtil.set_RTC()`](../firmware/wifi_client.py) uses `NTP.utc_ns`, not `NTP.datetime`, because the latter calls `time.localtime` and can shift fields on some ports). `time.time()` is therefore Unix UTC; `TZ` does not change the RTC. |

### Air Station (Wi‑Fi) — when data is not transmitted

In [`AirStation.tick()`](../firmware/models/air_station.py), measurements are only queued when **all** of the following hold: Wi‑Fi is connected, `runtime_settings['rtc_is_set']` is true (NTP after Wi‑Fi), and **`latitude`**, **`longitude`**, and **`height`** in `settings.toml` are each **non-empty** after stripping whitespace (so `"0"` is allowed for height). Otherwise the firmware logs **`DATA CANNOT BE TRANSMITTED, not all configurations have been made:`** followed by a semicolon-separated list of what is still missing (that warning is emitted again only when the set of blockers changes).

### `MODEL` values (`LdProduct`)

| Value | Constant |
|------:|----------|
| 1 | `AIR_AROUND` (also `AIR_BIKE` uses the same device class) |
| 2 | `AIR_CUBE` |
| 3 | `AIR_STATION` |
| 4 | `AIR_BADGE` |
| 5 | `AIR_BIKE` |

### `measurement_interval` (`AirStationMeasurementInterval`)

Common values (seconds): `30`, `60`, `180`, `300`, `600`, `900`, `1800`, `3600` (see enum names `sec30`, `min1`, `min3`, … in [`enums.py`](../firmware/enums.py)).

### How URLs are chosen at runtime

After `Config.init()`, `Config.set_api_url()` fills `Config.runtime_settings['API_URL']`:

- **Air Station, wifiless:** `DATAHUB_*_API_URL` (same as portable products).
- **Air Station, Wi‑Fi:** `API_URL` or `TEST_API_URL` from `boot.toml` depending on `TEST_MODE`.
- **Air Cube, Air Badge, Air aRound / Bike:** always the Datahub base (`DATAHUB_API_URL` or `DATAHUB_TEST_API_URL`).

`Config.runtime_settings['UPDATE_SERVER']` is set from `UPDATE_SERVER` or `TEST_UPDATE_SERVER` based on `TEST_MODE`.

### Enterprise Wi‑Fi

[`wifi_client.py`](../firmware/wifi_client.py) uses `EAP_IDENTITY`, `EAP_USERNAME`, and `EAP_PASSWORD` when `PASSWORD` is empty and all three are truthy. Those keys are registered in [`firmware/ugm/config.py`](../firmware/ugm/config.py); the main [`firmware/config.py`](../firmware/config.py) does **not** list them in `key_to_toml_file` today. For enterprise mode on the main app build, add the same keys to `Config.key_to_toml_file` and the `AutoSaveDict` defaults if you need them to load and persist from `settings.toml`.

---

## Runtime settings (`Config.runtime_settings`)

Not stored in `settings.toml` / `boot.toml`. Examples:

| Key | Role |
|-----|------|
| `API_URL` | Effective measurement API base after `set_api_url()`. |
| `UPDATE_SERVER` | Effective OTA server after `Config.init()`. |
| `rtc_is_set` | Whether NTP (or similar) has set the clock. |
| `CALIBRATION_MODE` | Resolved calibration flag for the session. |
| `JSON_QUEUE`, `FIRMWARE_FOLDER` | Local paths for queued JSON / OTA folder. |
| `SENSOR_COMMUNITY_API`, `SENSOR_COMMUNITY_CERTIFICATE_PATH` | Sensor.Community upload endpoint and CA bundle. |
| `API_KEY_LENGTH` | Length used when generating `api_key`. |

---

## Related files

- **One-shot boot flags** (RTC sync, model detect, SD upload, SD wipe): [`firmware/startup.toml`](../firmware/startup.toml) — separate from `settings.toml` / `boot.toml`; read by startup helpers, not `AutoSaveDict`.
- **JSON shapes sent to APIs:** [`docs/api-json.md`](api-json.md).
- **Bluetooth GATT (custom service, characteristics, Air Station TLV):** [`docs/ble-characteristics.md`](ble-characteristics.md). **`TZ`** is not configurable over BLE; use `settings.toml`.
