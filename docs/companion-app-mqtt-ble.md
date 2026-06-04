# Companion app: MQTT / Home Assistant over BLE

This document is for the **mobile app** (separate repository). It specifies how to read and write the same `MQTT_*` keys as [`docs/settings.md`](settings.md) using the existing Luftdaten GATT service.

## Service and characteristic

| Item | UUID / name |
|------|----------------|
| Service | `0931b4b5-2917-4a8d-9e72-23103c09ac29` |
| Command (write) | `030ff8b1-1e45-4ae6-bf36-3bca4c38cdba` (`trigger_reading_characteristic_2`) |
| Air Station config (read) | `b47b0cdf-0ced-49a9-86a5-d78a03ea7674` (`air_station_configuration`) |
| SD log export (read, wifiless Station/Cube; command `0x08`) | `51d2f8a4-91c6-53b2-a6e5-71829304a505` (`sd_log_export_characteristic`) |
| Device status (read) | `77db81d9-9773-49b4-aa17-16a2f93e95f2` (`device_status_characteristic`) — 5 bytes: battery, Wi‑Fi detail, operational flags (config / Wi‑Fi / no sensor) |

Full GATT documentation: [`docs/ble-characteristics.md`](ble-characteristics.md) (see **device_status_characteristic**).

## TLV encoding (shared)

After the **first command byte**, the payload is a sequence of records:

```text
[ flag: u8 ][ length: u8 ][ value: length bytes ]  (repeated)
```

- **Integer fields:** `value` is **4 bytes** big-endian signed int32; `length` must be `4`.
- **String fields:** `value` is UTF-8 bytes; `length` is `len(value)`.

## Command bytes

| Model | First byte | Notes |
|-------|------------|--------|
| **Air Station** | `0x06` (`SET_AIR_STATION_CONFIGURATION`) | Wi‑Fi / geo (`0…8`), MQTT (`9…17`), **`TZ` (`18`)**, **`LOG_LEVEL` (`19`)**, **`api_key` (`20`)**, **`startup.toml` one-shots (`21…25`)** — not MQTT; **`0x07` not** used for these. Also **`0x08`** (**`SD_LOG_EXPORT`**) to stream **wifiless** SD JSONL (see BLE doc UUID `51d2f8a4-…`). |
| **Air Cube** | `0x07` (`SET_CUBE_MQTT_CONFIGURATION`) | **MQTT flags only** (`9…17`); same record layout as Station. **`0x08`** (**`SD_LOG_EXPORT`**) when **wifiless** to stream SD JSONL. |

## MQTT flags (`AirstationConfigFlags`)

| Flag (dec) | Setting key | Value type |
|-----------|-------------|------------|
| `9` | `MQTT_ENABLED` | int32 `0` / `1` |
| `10` | `MQTT_BROKER` | UTF-8 string |
| `11` | `MQTT_PORT` | int32 |
| `12` | `MQTT_USE_TLS` | int32 `0` / `1` |
| `13` | `MQTT_USERNAME` | UTF-8 string |
| `14` | `MQTT_PASSWORD` | UTF-8 string (**write-only**; not returned on read) |
| `15` | `MQTT_DISCOVERY_PREFIX` | UTF-8 string |
| `16` | `MQTT_DEVICE_NAME` | UTF-8 string |
| `17` | `MQTT_CERTIFICATE_PATH` | UTF-8 string (optional) |

## App UI checklist

- **Screen section:** “Home Assistant / MQTT” with fields matching the table above and a master enable toggle.
- **Air Station save:** write `0x06` + concatenated TLV records (split across multiple writes if the buffer exceeds ~512 bytes / MTU — send subsets of records per write).
- **Air Cube save:** write `0x07` + TLV records for the keys the user changed (or full set).
- **Read-back (Station only):** after a successful write, read `air_station_configuration` and parse TLV to refresh non-secret fields. **Do not** expect `MQTT_PASSWORD` or Wi‑Fi password in the read blob.
- **Cube read-back:** there is no dedicated read characteristic for MQTT; keep the entered values in the app session or re-read after reconnect.
- **Password UX:** mask in UI; consider sending `MQTT_PASSWORD` only when the user edits it (product choice).
- **Capability gating:** hide MQTT UI when firmware version (from `device_info` JSON or binary layout) is below the release that added flags `9…17`.
- **Security:** prefer **LE Secure Connections / bonding** when exchanging broker passwords over BLE.

## Verification (Wi‑Fi / geo on Air Station)

GATT **write success ≠ settings saved**. After `0x06`:

1. **Device serial** (`LOG_LEVEL = DEBUG`): look for `BLE 0x06 TLV …` and `BLE config applied: …`.
2. **Read-back** (Station only): read `air_station_configuration` and parse TLV — **latitude/longitude/height** should match; **SSID/password are never** in this blob.
3. **USB**: open `settings.toml` on CIRCUITPY — confirm `SSID`, `PASSWORD`, `latitude`, `longitude`, `height`.
4. **Host tools** (this repo): `python3 tools/ble_tlv_reference.py` (valid example packets); `python3 tools/ble_tlv_verify.py <hex>` to parse an app capture.

**Common app bugs:** bitmask instead of per-field TLV; command `0x06` duplicated inside TLV; wrong string `length`; payload &gt; 512 bytes truncated.

## Related firmware modules

- TLV parse/apply: [`firmware/ble_config_tlv.py`](../firmware/ble_config_tlv.py)
- MQTT records: [`firmware/mqtt_ble_tlv.py`](../firmware/mqtt_ble_tlv.py)
- MQTT / HA runtime: [`firmware/mqtt_ha.py`](../firmware/mqtt_ha.py)
- Air Station decode/encode: [`firmware/models/air_station.py`](../firmware/models/air_station.py)
- Air Cube command `0x07`: [`firmware/models/air_cube.py`](../firmware/models/air_cube.py)
