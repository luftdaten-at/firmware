"""Host-side TLV codec (no CircuitPython deps). Mirrors firmware/ble_config_tlv.py."""

import struct
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "firmware"))

from enums import AirstationConfigFlags, BleCommands  # noqa: E402

_SECRET_FLAGS = frozenset(
    (
        AirstationConfigFlags.PASSWORD,
        AirstationConfigFlags.MQTT_PASSWORD,
        AirstationConfigFlags.API_KEY,
    )
)

_FLAG_LABELS = {
    AirstationConfigFlags.AUTO_UPDATE_MODE: "auto_update_mode",
    AirstationConfigFlags.BATTERY_SAVE_MODE: "battery_save_mode",
    AirstationConfigFlags.MEASUREMENT_INTERVAL: "measurement_interval",
    AirstationConfigFlags.LONGITUDE: "longitude",
    AirstationConfigFlags.LATITUDE: "latitude",
    AirstationConfigFlags.HEIGHT: "height",
    AirstationConfigFlags.SSID: "SSID",
    AirstationConfigFlags.PASSWORD: "PASSWORD",
    AirstationConfigFlags.DEVICE_ID: "DEVICE_ID",
    AirstationConfigFlags.MQTT_ENABLED: "MQTT_ENABLED",
    AirstationConfigFlags.MQTT_BROKER: "MQTT_BROKER",
    AirstationConfigFlags.MQTT_PORT: "MQTT_PORT",
    AirstationConfigFlags.MQTT_USE_TLS: "MQTT_USE_TLS",
    AirstationConfigFlags.MQTT_USERNAME: "MQTT_USERNAME",
    AirstationConfigFlags.MQTT_PASSWORD: "MQTT_PASSWORD",
    AirstationConfigFlags.MQTT_DISCOVERY_PREFIX: "MQTT_DISCOVERY_PREFIX",
    AirstationConfigFlags.MQTT_DEVICE_NAME: "MQTT_DEVICE_NAME",
    AirstationConfigFlags.MQTT_CERTIFICATE_PATH: "MQTT_CERTIFICATE_PATH",
    AirstationConfigFlags.TZ: "TZ",
    AirstationConfigFlags.LOG_LEVEL: "LOG_LEVEL",
    AirstationConfigFlags.API_KEY: "api_key",
}

_INT32_FLAGS = frozenset(
    (
        AirstationConfigFlags.AUTO_UPDATE_MODE,
        AirstationConfigFlags.BATTERY_SAVE_MODE,
        AirstationConfigFlags.MEASUREMENT_INTERVAL,
        AirstationConfigFlags.MQTT_ENABLED,
        AirstationConfigFlags.MQTT_PORT,
        AirstationConfigFlags.MQTT_USE_TLS,
    )
)


def flag_label(flag):
    return _FLAG_LABELS.get(flag, "unknown(%d)" % flag)


def iter_tlv_records(data):
    idx = 0
    data = bytes(data)
    n = len(data)
    while idx < n:
        if idx + 2 > n:
            break
        flag = data[idx]
        length = data[idx + 1]
        idx += 2
        if idx + length > n:
            break
        yield flag, data[idx : idx + length]
        idx += length


def format_tlv_payload_for_log(data):
    parts = []
    for flag, chunk in iter_tlv_records(data):
        label = flag_label(flag)
        if flag in _SECRET_FLAGS:
            parts.append("%s(len=%d,<redacted>)" % (label, len(chunk)))
        elif flag in _INT32_FLAGS:
            if len(chunk) == 4:
                parts.append("%s=%d" % (label, struct.unpack(">i", chunk)[0]))
            else:
                parts.append("%s(bad_len=%d)" % (label, len(chunk)))
        else:
            try:
                s = chunk.decode("utf-8")
                if len(s) > 24:
                    s = s[:21] + "..."
                parts.append('%s="%s"' % (label, s))
            except Exception:
                parts.append("%s(len=%d,?)" % (label, len(chunk)))
    return "[" + ", ".join(parts) + "]" if parts else "(empty)"


def pack_tlv_record(flag, value):
    if isinstance(value, str):
        value_bytes = value.encode("utf-8")
    elif isinstance(value, bool):
        value_bytes = struct.pack(">i", 1 if value else 0)
    elif isinstance(value, int):
        value_bytes = struct.pack(">i", value)
    else:
        value_bytes = bytes(value)
    if len(value_bytes) > 255:
        raise ValueError("TLV value too long (%d)" % len(value_bytes))
    return bytes([flag, len(value_bytes)]) + value_bytes


def pack_air_station_command(*records):
    body = b"".join(records)
    return bytes([BleCommands.SET_AIR_STATION_CONFIGURATION]) + body
