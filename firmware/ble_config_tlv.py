"""
Air Station / Air Cube BLE configuration TLV helpers.

Record layout (after command byte 0x06 or 0x07):
  [ flag: u8 ][ length: u8 ][ value: length bytes ]  (repeated)

See docs/ble-characteristics.md and docs/companion-app-mqtt-ble.md.
"""

import struct

from enums import AirstationConfigFlags
from logger import logger

# Flags whose value must not appear in debug logs (length only).
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
    AirstationConfigFlags.DEVICE_ID: "DEVICE_ID(read-only)",
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
    AirstationConfigFlags.SYNC_RTC_FROM_NTP: "startup:SYNC_RTC_FROM_NTP",
    AirstationConfigFlags.DETECT_MODEL_FROM_SENSORS: "startup:DETECT_MODEL_FROM_SENSORS",
    AirstationConfigFlags.UPLOAD_SD_LOG_TO_DATAHUB: "startup:UPLOAD_SD_LOG_TO_DATAHUB",
    AirstationConfigFlags.CLEAR_SD_CARD: "startup:CLEAR_SD_CARD",
    AirstationConfigFlags.REFRESH_SENSORS: "startup:REFRESH_SENSORS",
}

_INT32_FLAGS = frozenset(
    (
        AirstationConfigFlags.AUTO_UPDATE_MODE,
        AirstationConfigFlags.BATTERY_SAVE_MODE,
        AirstationConfigFlags.MEASUREMENT_INTERVAL,
        AirstationConfigFlags.MQTT_ENABLED,
        AirstationConfigFlags.MQTT_PORT,
        AirstationConfigFlags.MQTT_USE_TLS,
        AirstationConfigFlags.SYNC_RTC_FROM_NTP,
        AirstationConfigFlags.DETECT_MODEL_FROM_SENSORS,
        AirstationConfigFlags.UPLOAD_SD_LOG_TO_DATAHUB,
        AirstationConfigFlags.CLEAR_SD_CARD,
        AirstationConfigFlags.REFRESH_SENSORS,
    )
)


def flag_label(flag):
    return _FLAG_LABELS.get(flag, "unknown(%d)" % flag)


def iter_tlv_records(data):
    """
    Yield (flag, value_bytes) from a TLV buffer (no leading command byte).
    Stops with a warning on truncated or malformed data.
    """
    idx = 0
    data = bytes(data)
    n = len(data)
    while idx < n:
        if idx + 2 > n:
            logger.warning(
                "ble_config_tlv: incomplete header at offset %d (%d bytes left)"
                % (idx, n - idx)
            )
            return
        flag = data[idx]
        length = data[idx + 1]
        idx += 2
        if idx + length > n:
            logger.warning(
                "ble_config_tlv: truncated record flag=%d (%s) len=%d at offset %d"
                % (flag, flag_label(flag), length, idx - 2)
            )
            return
        yield flag, data[idx : idx + length]
        idx += length


def format_tlv_payload_for_log(data):
    """Summarize TLV records for serial DEBUG (no secret values)."""
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
    """Build one TLV record (flag, length, value) for reference encoders / tests."""
    if isinstance(value, str):
        value_bytes = value.encode("utf-8")
    elif isinstance(value, bool):
        value_bytes = struct.pack(">i", 1 if value else 0)
    elif isinstance(value, int):
        value_bytes = struct.pack(">i", value)
    else:
        value_bytes = bytes(value)
    if len(value_bytes) > 255:
        raise ValueError("TLV value too long for u8 length (%d)" % len(value_bytes))
    return bytes([flag, len(value_bytes)]) + value_bytes


def pack_air_station_command(*records):
    """Return full write buffer: 0x06 + concatenated TLV records."""
    from enums import BleCommands

    body = b"".join(records)
    return bytes([BleCommands.SET_AIR_STATION_CONFIGURATION]) + body


def decode_air_station_tlv(data, startup_flag_pairs):
    """
    Apply TLV payload from SET_AIR_STATION_CONFIGURATION (no 0x06 prefix).

    ``startup_flag_pairs``: iterable of (flag_int, startup_toml_key) from air_station.

    Returns (wifi_config_changed, mqtt_changed, applied_labels).
    """
    from config import Config
    from mqtt_ble_tlv import apply_mqtt_tlv_record
    from startup_actions import set_startup_flag

    wifi_config_changed = False
    mqtt_changed = False
    applied = []
    rejected = 0

    logger.debug(
        "BLE 0x06 TLV %d bytes: %s" % (len(data), format_tlv_payload_for_log(data))
    )

    for flag, chunk in iter_tlv_records(data):
        label = flag_label(flag)
        try:
            if flag == AirstationConfigFlags.DEVICE_ID:
                logger.warning(
                    "ble_config_tlv: flag %d (%s) is read-only; ignored"
                    % (flag, label)
                )
                rejected += 1
                continue

            if flag == AirstationConfigFlags.AUTO_UPDATE_MODE:
                if len(chunk) != 4:
                    raise ValueError("expected 4 bytes, got %d" % len(chunk))
                Config.settings["auto_update_mode"] = struct.unpack(">i", chunk)[0]
                applied.append(label)

            elif flag == AirstationConfigFlags.BATTERY_SAVE_MODE:
                if len(chunk) != 4:
                    raise ValueError("expected 4 bytes, got %d" % len(chunk))
                Config.settings["battery_save_mode"] = struct.unpack(">i", chunk)[0]
                applied.append(label)

            elif flag == AirstationConfigFlags.MEASUREMENT_INTERVAL:
                if len(chunk) != 4:
                    raise ValueError("expected 4 bytes, got %d" % len(chunk))
                Config.settings["measurement_interval"] = struct.unpack(">i", chunk)[0]
                applied.append(label)

            elif flag == AirstationConfigFlags.LONGITUDE:
                Config.settings["longitude"] = chunk.decode("utf-8")
                applied.append(label)

            elif flag == AirstationConfigFlags.LATITUDE:
                Config.settings["latitude"] = chunk.decode("utf-8")
                applied.append(label)

            elif flag == AirstationConfigFlags.HEIGHT:
                Config.settings["height"] = chunk.decode("utf-8")
                applied.append(label)

            elif flag == AirstationConfigFlags.SSID:
                Config.settings["SSID"] = chunk.decode("utf-8")
                wifi_config_changed = True
                applied.append(label)

            elif flag == AirstationConfigFlags.PASSWORD:
                Config.settings["PASSWORD"] = chunk.decode("utf-8")
                wifi_config_changed = True
                applied.append(label)

            elif flag == AirstationConfigFlags.TZ:
                Config.settings["TZ"] = chunk.decode("utf-8")
                applied.append(label)

            elif flag == AirstationConfigFlags.LOG_LEVEL:
                Config.settings["LOG_LEVEL"] = chunk.decode("utf-8")
                applied.append(label)

            elif flag == AirstationConfigFlags.API_KEY:
                Config.settings["api_key"] = chunk.decode("utf-8")
                applied.append(label)

            elif (
                AirstationConfigFlags.MQTT_ENABLED
                <= flag
                <= AirstationConfigFlags.MQTT_CERTIFICATE_PATH
            ):
                if apply_mqtt_tlv_record(flag, chunk):
                    mqtt_changed = True
                    applied.append(label)
                else:
                    logger.warning(
                        "ble_config_tlv: MQTT flag %d (%s) rejected (bad length or decode)"
                        % (flag, label)
                    )
                    rejected += 1

            else:
                handled = False
                for startup_flag, startup_key in startup_flag_pairs:
                    if flag == startup_flag:
                        if len(chunk) != 4:
                            raise ValueError(
                                "startup flag %s needs int32 len=4, got %d"
                                % (startup_key, len(chunk))
                            )
                        v_raw = struct.unpack(">i", chunk)[0]
                        set_startup_flag(startup_key, bool(v_raw))
                        applied.append(label)
                        handled = True
                        break
                if not handled:
                    logger.warning(
                        "ble_config_tlv: unknown or unsupported flag %d"
                        % flag
                    )
                    rejected += 1

        except Exception as e:
            logger.warning(
                "ble_config_tlv: rejected flag %d (%s): %s: %s"
                % (flag, label, type(e).__name__, e)
            )
            rejected += 1

    if applied:
        logger.info("BLE config applied: %s" % ", ".join(applied))
    if rejected:
        logger.warning("BLE config: %d record(s) rejected" % rejected)

    return wifi_config_changed, mqtt_changed, applied
