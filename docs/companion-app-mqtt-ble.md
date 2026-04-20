# Companion app: MQTT / Home Assistant over BLE

This document is for the **mobile app** (separate repository). It specifies how to read and write the same `MQTT_*` keys as [`docs/settings.md`](settings.md) using the existing Luftdaten GATT service.

## Service and characteristic

| Item | UUID / name |
|------|----------------|
| Service | `0931b4b5-2917-4a8d-9e72-23103c09ac29` |
| Command (write) | `030ff8b1-1e45-4ae6-bf36-3bca4c38cdba` (`trigger_reading_characteristic_2`) |
| Air Station config (read) | `b47b0cdf-0ced-49a9-86a5-d78a03ea7674` (`air_station_configuration`) |

Full GATT documentation: [`docs/ble-characteristics.md`](ble-characteristics.md).

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
| **Air Station** | `0x06` (`SET_AIR_STATION_CONFIGURATION`) | May include Wi‑Fi / geo TLVs (`0…8`) **and** MQTT TLVs (`9…17`) in one or multiple writes. |
| **Air Cube** | `0x07` (`SET_CUBE_MQTT_CONFIGURATION`) | **MQTT flags only** (`9…17`); same record layout as Station. |

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

## Related firmware modules

- TLV apply logic: [`firmware/mqtt_ble_tlv.py`](../firmware/mqtt_ble_tlv.py)
- MQTT / HA runtime: [`firmware/mqtt_ha.py`](../firmware/mqtt_ha.py)
- Air Station decode/encode: [`firmware/models/air_station.py`](../firmware/models/air_station.py)
- Air Cube command `0x07`: [`firmware/models/air_cube.py`](../firmware/models/air_cube.py)
