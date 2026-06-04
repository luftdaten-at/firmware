"""Decode MQTT / Home Assistant settings from Air Station (0x06) or Air Cube (0x07) TLV."""

import struct

from config import Config
from enums import AirstationConfigFlags
from logger import logger


def _set_if_changed(key: str, new_val) -> bool:
    if Config.settings.get(key) != new_val:
        Config.settings[key] = new_val
        return True
    return False


def apply_mqtt_tlv_record(flag: int, value_bytes) -> bool:
    """
    Apply a single TLV record body (flag already consumed).
    Returns True if any ``MQTT_*`` setting changed.
    """
    changed = False
    try:
        if flag == AirstationConfigFlags.MQTT_ENABLED:
            if len(value_bytes) != 4:
                return False
            v = struct.unpack(">i", value_bytes)[0]
            changed |= _set_if_changed("MQTT_ENABLED", bool(v))

        elif flag == AirstationConfigFlags.MQTT_BROKER:
            s = value_bytes.decode("utf-8")
            changed |= _set_if_changed("MQTT_BROKER", s)

        elif flag == AirstationConfigFlags.MQTT_PORT:
            if len(value_bytes) != 4:
                return False
            v = struct.unpack(">i", value_bytes)[0]
            changed |= _set_if_changed("MQTT_PORT", int(v))

        elif flag == AirstationConfigFlags.MQTT_USE_TLS:
            if len(value_bytes) != 4:
                return False
            v = struct.unpack(">i", value_bytes)[0]
            changed |= _set_if_changed("MQTT_USE_TLS", bool(v))

        elif flag == AirstationConfigFlags.MQTT_USERNAME:
            s = value_bytes.decode("utf-8")
            changed |= _set_if_changed("MQTT_USERNAME", s)

        elif flag == AirstationConfigFlags.MQTT_PASSWORD:
            s = value_bytes.decode("utf-8")
            changed |= _set_if_changed("MQTT_PASSWORD", s)

        elif flag == AirstationConfigFlags.MQTT_DISCOVERY_PREFIX:
            s = value_bytes.decode("utf-8")
            changed |= _set_if_changed("MQTT_DISCOVERY_PREFIX", s)

        elif flag == AirstationConfigFlags.MQTT_DEVICE_NAME:
            s = value_bytes.decode("utf-8")
            changed |= _set_if_changed("MQTT_DEVICE_NAME", s)

        elif flag == AirstationConfigFlags.MQTT_CERTIFICATE_PATH:
            s = value_bytes.decode("utf-8")
            changed |= _set_if_changed("MQTT_CERTIFICATE_PATH", s)

    except Exception as e:
        logger.warning(f"mqtt_ble_tlv: flag {flag} decode error: {e}")
        return False

    return changed


def decode_mqtt_settings_tlv(data) -> bool:
    """
    Walk a full TLV buffer (no leading command byte) for MQTT flags only.
    Used by Air Cube ``0x07`` payload.
    """
    from ble_config_tlv import format_tlv_payload_for_log, iter_tlv_records

    data = bytes(data)
    logger.debug(
        "BLE 0x07 MQTT TLV %d bytes: %s"
        % (len(data), format_tlv_payload_for_log(data))
    )
    changed = False
    applied = []
    for flag, chunk in iter_tlv_records(data):
        if (
            AirstationConfigFlags.MQTT_ENABLED
            <= flag
            <= AirstationConfigFlags.MQTT_CERTIFICATE_PATH
        ):
            if apply_mqtt_tlv_record(flag, chunk):
                changed = True
            applied.append(flag)
        else:
            logger.warning(
                "mqtt_ble_tlv: flag %d ignored on 0x07 (MQTT flags 9-17 only)"
                % flag
            )
    if applied:
        logger.info("BLE MQTT config applied: flags %s" % applied)
    return changed
