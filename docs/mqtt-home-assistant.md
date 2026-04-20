# Home Assistant MQTT (Air Cube & Air Station Wi‑Fi)

The firmware can publish **MQTT Discovery** messages so [Home Assistant](https://www.home-assistant.io/) creates **sensors** automatically, plus **availability** (online/offline) and **state** updates on each measurement (same cadence as Datahub uploads where applicable).

## Requirements

- **Air Cube** or **Air Station** with **Wi‑Fi** (not wifiless SD mode).
- A reachable **MQTT broker** (e.g. [Mosquitto](https://mosquitto.org/) as the [Home Assistant MQTT add-on](https://www.home-assistant.io/addons/mosquitto/)).
- In Home Assistant: **Settings → Devices & services → Add integration → MQTT** using the **same broker, port, user, and password** as in the device `settings.toml` (or as provisioned over BLE).

## `settings.toml` keys

See [`docs/settings.md`](settings.md) for the full table. Summary:

| Key | Role |
|-----|------|
| `MQTT_ENABLED` | `true` / `false` — master switch. |
| `MQTT_BROKER` | Broker hostname or IP (required when enabled). |
| `MQTT_PORT` | Broker port (e.g. `1883` plain, `8883` TLS). |
| `MQTT_USE_TLS` | Use TLS (`ssl`); must match broker. |
| `MQTT_USERNAME` / `MQTT_PASSWORD` | Optional broker auth. |
| `MQTT_DISCOVERY_PREFIX` | HA discovery prefix (default `homeassistant`). |
| `MQTT_DEVICE_NAME` | Friendly **device** name in HA (optional). |
| `MQTT_CERTIFICATE_PATH` | Optional PEM path for broker CA verification; if empty, the firmware uses `CERTIFICATE_PATH` from `boot.toml` (same as HTTPS). |

## Topics (firmware contract)

- **State / discovery base:** `luftdaten/<device_id>/…` (device id normalized for MQTT path segments).
- **Per-metric state:** `luftdaten/<device_id>/s<slot>_d<dimension_id>/state` (numeric string payload).
- **Discovery:** `<MQTT_DISCOVERY_PREFIX>/sensor/<object_id>/config` (JSON, **retained**).
- **Availability:** `luftdaten/<device_id>/availability` with payloads `online` / `offline`; **Last Will** publishes retained `offline` if the connection drops unexpectedly.

## Configure from the mobile app (BLE)

Air Station uses command **`0x06`** and Air Cube uses **`0x07`** with the same TLV **flag** bytes `9…17` as in [`docs/ble-characteristics.md`](ble-characteristics.md). App specification: [`docs/companion-app-mqtt-ble.md`](companion-app-mqtt-ble.md).

## Verify in Home Assistant

1. Enable MQTT in HA and confirm the broker shows a new client when the device connects.
2. **Settings → Devices & services → MQTT → Configure** — check the device list / entities.
3. Open **Developer tools → States** and filter by your device name or `luftdaten`.

## Troubleshooting

- **No entities:** confirm `MQTT_ENABLED`, broker host, port, TLS flag, and credentials; check device logs for `MqttHa connect failed`.
- **TLS errors:** set `MQTT_CERTIFICATE_PATH` to a PEM that verifies your broker, or use a public chain broker with the default `CERTIFICATE_PATH`.
- **RAM:** discovery runs once per metric after connect; many sensors increase retained config traffic — consider disabling unused sensors or MQTT if the board becomes unstable.
