# JSON payloads sent to APIs

This document describes the **JSON object shapes** produced by the firmware and sent over HTTP. It reflects the current code in [`firmware/models/ld_product_model.py`](../firmware/models/ld_product_model.py), [`firmware/models/air_station.py`](../firmware/models/air_station.py), and [`firmware/wifi_client.py`](../firmware/wifi_client.py). Field names and nesting match what `json=` sends on the wire.

The top-level metadata object uses the key **`device`** ([`API_JSON_DEVICE_KEY`](../firmware/models/ld_product_model.py)); the inner field **`device`** (string) is still the **device ID** (`device_id` from settings).

## Base URLs and routes

| Use case | Base URL (from config) | HTTP path | Typical caller |
|----------|-------------------------|-----------|------------------|
| Datahub measurement / initial device info | `DATAHUB_API_URL` or `DATAHUB_TEST_API_URL` (`settings.toml` / `boot.toml`) | `data/` (default router) | [`WifiUtil.send_json_to_api(..., router='data/')`](../firmware/wifi_client.py) — e.g. [`LdProductModel`](../firmware/models/ld_product_model.py) boot `get_initial_info` |
| Datahub status + logs | Same datahub base | `status/` | [`send_to_api`](../firmware/models/ld_product_model.py) tail |
| Station measurement API | `API_URL` / `TEST_API_URL` → [`Config.runtime_settings['API_URL']`](../firmware/config.py) after `set_api_url()` | `data/` (default) | Queued `send_json_to_api(data)` without overriding `api_url` |
| Sensor.Community | `SENSOR_COMMUNITY_API` in runtime | full URL constant | [`send_json_to_sensor_community`](../firmware/wifi_client.py) with extra **headers** |

Full URL pattern for datahub HTTP session: **`{base}/{router}`** (e.g. `https://…/data/`).

---

## Shared envelope: `device` + `sensors`

Most payloads are built from [`get_info()`](../firmware/models/ld_product_model.py) and optionally extended in subclasses (e.g. Air Station).

### `get_info()` — top-level `device` object

```json
{
  "device": {
    "time": "2026-04-16T12:00:00.000Z",
    "device": "<device_id>",
    "firmware": "<major>.<minor>.<patch>",
    "model": <integer model id>,
    "apikey": "<api_key>",
    "source": 1,
    "test_mode": <boolean>,
    "calibration_mode": <boolean>
  },
  "sensors": {}
}
```

- **`time`**: ISO-like UTC string from `time.localtime()` (not necessarily true UTC without NTP/RTC).
- **`model`**: [`LdProduct`](../firmware/enums.py) integer (e.g. Air Station = 3).
- **`sensors`**: Empty object here; filled in [`get_json()`](../firmware/models/ld_product_model.py).

### Air Station — extra `device.location`

[`AirStation.get_info()`](../firmware/models/air_station.py) adds:

```json
"device": {
  …,
  "location": {
    "lat": "<string or null>",
    "lon": "<string or null>",
    "height": "<string or null>"
  }
}
```

Values come from `settings.toml` (`latitude`, `longitude`, `height`).

### Portable models (Air aRound / Bike, Cube, Badge) — extra `device` fields

Subclasses may extend the **`device`** object for BLE/API metadata, e.g. [`AirAround.get_info()`](../firmware/models/air_around.py):

```json
"device": {
  …,
  "api": { "key": "<api_key>" },
  "battery": {
    "voltage": <float or null>,
    "percentage": <float or null>
  }
}
```

[`AirCube.get_info()`](../firmware/models/air_cube.py) and [`AirBadge.get_info()`](../firmware/models/air_badge.py) add **`device.battery`** only (same shape as above, no **`device.api`**).

---

## Measurement payload: `get_json()`

Used for:

- Queued POSTs to **`{API_URL}/data/`** (default router) when flushing `measurements['normal']`.
- Air Station **wifiless** SD log lines (same structure, one JSON object per line in [`append_measurement_jsonl`](../firmware/sd_logger.py)).

Built in [`get_json()`](../firmware/models/ld_product_model.py):

```json
{
  "device": { … },
  "sensors": {
    "0": {
      "type": <sensor model_id>,
      "data": { "<dimension_id>": <value>, … }
    },
    "1": { … }
  }
}
```

- **Keys** under `sensors` are stringified indices `0`, `1`, … (enumeration order).
- **`type`**: sensor hardware model id ([`SensorModel`](../firmware/enums.py)).
- **`data`**: map of dimension id → current reading (types depend on sensor; may include `null`).

---

## Initial datahub registration: `get_initial_info()`

On first successful Wi‑Fi after boot (non–wifiless path), [`LdProductModel.__init__`](../firmware/models/ld_product_model.py) POSTs to **datahub** `data/` with [`get_initial_info()`](../firmware/models/ld_product_model.py): same as `get_info()` but the **`device`** object also contains **`sensor_list`**:

```json
{
  "device": {
    "time": "…",
    "device": "…",
    "firmware": "…",
    "model": <int>,
    "apikey": "…",
    "source": 1,
    "test_mode": <bool>,
    "calibration_mode": <bool>,
    "sensor_list": [
      {
        "model_id": <int>,
        "dimension_list": [ … ],
        "serial_number": "<string>"
      }
    ]
  },
  "sensors": {}
}
```

---

## Status payload: datahub `status/`

After draining measurement queues, [`send_to_api`](../firmware/models/ld_product_model.py) POSTs to **`DATAHUB_API_URL` / `DATAHUB_TEST_API_URL`** with router **`status/`** (not the Air Station `API_URL`):

```json
{
  "device": { … },
  "sensors": {},
  "status_list": [
    {
      "time": "2026-04-16T12:00:00.000Z",
      "level": <0–4 int, LOG_LEVELS>,
      "message": "<string>"
    }
  ]
}
```

- **`status_list`**: entries from [`logger.log_list`](../firmware/logger.py) (`SimpleLogger.save`). Cleared on HTTP 200.
- Response may include **`flags`** with `test_mode` / `calibration_mode`; the firmware can update `settings.toml` and reload (see same function).

---

## Sensor.Community

Not a single combined JSON: each item is **`(header_dict, body_dict)`**; [`send_json_to_sensor_community`](../firmware/wifi_client.py) sends **`POST`** with `json=body` and `headers=header`.

### Headers (per request)

```http
Content-Type: application/json
X-Pin: "<pin string>"
X-Sensor: "<device_id>"
```

`X-Pin` is e.g. `"9"` for the GPS/meta block on Air Station, or [`SensorModel.get_pin(sensor.model_id)`](../firmware/enums.py) per sensor.

### Body — GPS / meta block (Air Station)

```json
{
  "software_version": "Luftdaten.at-<major>.<minor>.<patch>",
  "sensordatavalues": [
    { "value_type": "latitude", "value": "<from settings>" },
    { "value_type": "longitude", "value": "<from settings>" },
    { "value_type": "height", "value": "<from settings>" }
  ]
}
```

### Body — per physical sensor

```json
{
  "software_version": "Luftdaten.at-<major>.<minor>.<patch>",
  "sensordatavalues": [
    { "value_type": "<sensor.community name>", "value": <reading> }
  ]
}
```

`value_type` comes from [`Dimension.get_sensor_community_name`](../firmware/enums.py).

---

## Implementation references

| Topic | File |
|--------|------|
| Build measurement + `device` block | [`LdProductModel.get_json` / `get_info`](../firmware/models/ld_product_model.py) |
| Air Station location + sensor.community list | [`AirStation`](../firmware/models/air_station.py) |
| HTTP POST | [`WifiUtil.send_json_to_api`](../firmware/wifi_client.py) (`router` defaults to `data/`) |
| Which base URL for measurements | [`Config.set_api_url`](../firmware/config.py) |

This document does **not** define server-side validation or optional fields accepted by each backend; it only mirrors what the device sends.
