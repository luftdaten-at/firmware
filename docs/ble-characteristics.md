# Bluetooth GATT: Luftdaten custom service

This document describes the **single custom BLE service** and its characteristics as implemented in [`firmware/ld_service.py`](../firmware/ld_service.py), how [`firmware/main.py`](../firmware/main.py) fills read characteristics, and how writes on the command characteristic are interpreted.

**Timezone:** There is **no** GATT characteristic and **no** Air Station configuration flag for **`TZ`** / IANA timezone. Timezone for API/log strings is configured in **`settings.toml`** only (see [`docs/settings.md`](settings.md)). To expose `TZ` over BLE in the future you would need a new `AirstationConfigFlags` value and matching app support.

---

## Service

| Item | Value |
|------|--------|
| Python class | [`LdService`](../firmware/ld_service.py) |
| Base class | `adafruit_ble.services.Service` |
| **128-bit service UUID** | `0931b4b5-2917-4a8d-9e72-23103c09ac29` (Adafruit `VendorUUID`) |

Advertising uses `ProvideServicesAdvertisement(service)` in [`main.py`](../firmware/main.py). The BLE name is `Luftdaten.at-` + `Config.settings['mac']`.

---

## Characteristics (overview)

All characteristics use **vendor UUIDs** (same namespace as the service). `max_length` is **512** where defined in code.

| Python attribute | UUID | Properties | Purpose |
|------------------|------|------------|---------|
| `air_station_configuration` | `b47b0cdf-0ced-49a9-86a5-d78a03ea7674` | READ | **Air Station:** TLV blob built by [`AirStation.encode_configurations()`](../firmware/models/air_station.py). Other models: initial `bytes([0])` (not updated in code paths shown). |
| `sensor_values_characteristic` | `4b439140-73cb-4776-b1f2-8f3711b3bb4f` | READ | Binary concatenation of each sensor’s [`Sensor.get_current_values()`](../firmware/sensors/sensor.py) (see [Sensor values binary](#sensor-values-binary)). Updated in [`LdProductModel.update_ble_sensor_data()`](../firmware/models/ld_product_model.py). |
| `device_info_characteristic` | `8d473240-13cb-1776-b1f2-823711b3ffff` | READ | **JSON** (UTF-8) when `api_key` is set at boot; else **legacy binary** (see [Device info](#device-info-characteristic)). Built in [`main.py`](../firmware/main.py). |
| `device_status_characteristic` | `77db81d9-9773-49b4-aa17-16a2f93e95f2` | READ | Four bytes: battery flag, SOC %, voltage×10, error code ([`update_ble_battery_status`](../firmware/models/ld_product_model.py)). |
| `sensor_info_characteristic` | `13fa8751-57af-4597-a0bb-b202f6111ae6` | READ | Concatenation of each sensor’s [`get_device_info()`](../firmware/sensors/sensor.py). If no sensors: `bytes([0x06])`. |
| `trigger_reading_characteristic_2` | `030ff8b1-1e45-4ae6-bf36-3bca4c38cdba` | WRITE, WRITE_NO_RESPONSE | **Command input:** first byte is [`BleCommands`](#ble-commands). Payload is read once per loop in [`main.py`](../firmware/main.py), then cleared. |

---

## Write path: `trigger_reading_characteristic_2`

After each connection poll, if the characteristic has been written, [`main.py`](../firmware/main.py) copies the value to `command`, clears the characteristic, then calls:

1. `device.receive_command(command)` — model-specific (sensors, Air Station config).
2. `device.status_led.receive_command(command)` — LED / brightness ([`LedController`](../firmware/led_controller.py)).

Both receive the **same** byte buffer.

### `BleCommands` ([`enums.py`](../firmware/enums.py))

| Value (hex) | Name | Handled by |
|-------------|------|------------|
| `0x01` | `READ_SENSOR_DATA` | Air aRound / Bike, Air Badge, Air Cube ([`receive_command`](../firmware/models/air_cube.py) etc.); triggers sensor read + BLE updates. |
| `0x02` | `READ_SENSOR_DATA_AND_BATTERY_STATUS` | Same models; also updates battery/status bytes. |
| `0x03` | `UPDATE_BRIGHTNESS` | [`LedController.receive_command`](../firmware/led_controller.py): second byte is brightness level index `0…4`. |
| `0x04` | `TURN_OFF_STATUS_LIGHT` | LED controller. |
| `0x05` | `TURN_ON_STATUS_LIGHT` | LED controller. |
| `0x06` | `SET_AIR_STATION_CONFIGURATION` | [`AirStation.receive_command`](../firmware/models/air_station.py): payload after `0x06` is TLV data (next section). |

Air Station does not implement `READ_SENSOR_DATA` in `receive_command`; only `SET_AIR_STATION_CONFIGURATION` is handled there.

### Air Station configuration TLV (`0x06`)

After the leading `0x06`, the payload is a sequence of records:

```text
[ flag: u8 ][ length: u8 ][ value: length bytes ]  (repeated)
```

- **String settings:** `value` is UTF-8; `length` is `len(value_bytes)`.
- **Integer settings:** `value` is **4 bytes** big-endian signed 32-bit (`struct.pack('>i', …)`); `length` is `4`.

[`AirstationConfigFlags`](../firmware/enums.py) (`flag` value → meaning):

| Flag | Name | `Config.settings` key | Value type |
|------|------|----------------------|------------|
| `0` | `AUTO_UPDATE_MODE` | `auto_update_mode` | int32 |
| `1` | `BATTERY_SAVE_MODE` | `battery_save_mode` | int32 |
| `2` | `MEASUREMENT_INTERVAL` | `measurement_interval` | int32 |
| `3` | `LONGITUDE` | `longitude` | UTF-8 string |
| `4` | `LATITUDE` | `latitude` | UTF-8 string |
| `5` | `HEIGHT` | `height` | UTF-8 string |
| `6` | `SSID` | `SSID` | UTF-8 string (triggers `WifiUtil.connect()` if changed) |
| `7` | `PASSWORD` | `PASSWORD` | UTF-8 string (same) |
| `8` | `DEVICE_ID` | — | Present in [`encode_configurations`](../firmware/models/air_station.py) for **read** TLV; **not** written in [`decode_configuration`](../firmware/models/air_station.py) (read-only over the wire from central’s perspective). |

**Read-back:** [`AirStation.send_configuration`](../firmware/models/air_station.py) assigns `air_station_configuration` from `encode_configurations()`, which includes flags `0…5` and `8` (`DEVICE_ID`), **not** SSID/password (secrets are not mirrored on the read characteristic).

---

## Read path: binary layouts

### Sensor values binary

From [`Sensor.get_current_values`](../firmware/sensors/sensor.py) per sensor, concatenated in bus order:

1. `model_id` — `u8`
2. `len(current_values)` — `u8`
3. For each dimension key in `current_values`:
   - dimension id — `u8`
   - value — **2 bytes** big-endian int16 = `round(physical_value * 10)`, or `0x00 0x00` if NaN / missing

### Sensor info binary

From [`Sensor.get_device_info`](../firmware/sensors/sensor.py):

1. `model_id` — `u8`
2. `len(measures_values)` — `u8`
3. `measures_values` bytes
4. `0xff` separator
5. `sensor_details` bytes
6. `0xff` terminator

Multiple sensors are concatenated without an extra header (count is implied by advertising / main setup).

### `device_info_characteristic`

**A) JSON path** — when `Config.settings['api_key']` is truthy at boot ([`main.py`](../firmware/main.py)):

- UTF-8 encoding of `json.dumps(device_info_json)`.
- `device_info_json` = `device.get_info()` plus `sensor_list` (model id, dimension list, serial per sensor).

The `device` object in JSON comes from [`LdProductModel.get_info()`](../firmware/models/ld_product_model.py): `time`, `device`, `firmware`, `model`, `apikey`, `source`, `test_mode`, `calibration_mode` — **not** `TZ`, `LOG_LEVEL`, or Wi‑Fi SSID.

**B) Binary path** — when `api_key` is missing (and on exception fallback):

| Offset | Field |
|--------|--------|
| 0 | `PROTOCOL_VERSION` (`u8`) |
| 1 | `FIRMWARE_MAJOR` (`u8`) |
| 2 | `FIRMWARE_MINOR` (`u8`) |
| 3 | `FIRMWARE_PATCH` (`u8`) |
| 4–7 | Reserved (zeros); “device name” not implemented |
| 8 | `MODEL` (`u8`, [`LdProduct`](../firmware/enums.py)) |
| 9… | `connected_sensors_status` (see below) |
| … | `api_key` length (`u8`, min(len, 255)) |
| … | `api_key` bytes (up to 255) |

**`connected_sensors_status`** ([`main.py`](../firmware/main.py)):

- Byte 0: count of connected sensors `N`
- Then `N` times: `[ sensor_model_id: u8 ][ 0x01: connected ]`

### `device_status_characteristic`

Four bytes (extended by error code in [`update_ble_error_status`](../firmware/models/ld_product_model.py)):

| Index | Meaning |
|-------|---------|
| 0 | `1` = battery monitor present, `0` = absent |
| 1 | Battery SOC % (rounded) |
| 2 | Battery voltage × 10 (rounded) |
| 3 | Error code (`0` = none) |

### `air_station_configuration` (read)

TLV format **same flag bytes as write**, but payload built only from non-secret fields in [`encode_configurations()`](../firmware/models/air_station.py) (flags 0–5 and 8 as in the table above).

---

## Not exposed over BLE (non-exhaustive)

These `settings.toml` / runtime items are **not** part of the Air Station TLV protocol and **not** in the JSON `device` blob today, including:

- **`TZ`** (timezone for [`format_iso8601_tz()`](../firmware/tz_format.py))
- **`LOG_LEVEL`**
- **`TEST_MODE`**, **`CALIBRATION_MODE`** (API/flags may change them; not BLE TLV)
- **`WIFILESS_MODE`**, **`SD_LOG_PATH`**, **`ROLLBACK`**, etc.

Configure them via **USB** (`settings.toml`) or extend the firmware protocol and mobile apps together.

---

## Related documentation

- [`docs/settings.md`](settings.md) — persistent keys including `TZ`.
- [`docs/api-json.md`](api-json.md) — HTTP JSON shapes (separate from BLE `device_info` JSON, though `get_info()` overlaps conceptually).
