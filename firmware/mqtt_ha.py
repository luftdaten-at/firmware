"""
Home Assistant MQTT: discovery, availability, per-metric state (MiniMQTT).

Publish-only. Used from ``main`` loop and from Air Cube / Air Station measurement paths.
"""

import gc
import json
from ssl import create_default_context

from config import Config
from enums import Dimension, LdProduct
from logger import logger
from wifi_client import WifiUtil

_mqtt = None
_last_broker_key = None
_discovery_sent_keys = set()
_discovery_dirty = False


def _coerce_bool(val, default=False):
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(int(val))
    s = str(val).strip().lower()
    return s in ("1", "true", "yes", "on")


def _model_supported():
    m = Config.settings.get("MODEL")
    if m == LdProduct.AIR_CUBE:
        return True
    if m == LdProduct.AIR_STATION and not Config.is_air_station_wifiless():
        return True
    return False


def _sanitize_object_id(part):
    out = []
    for c in str(part).lower():
        if c.isalnum() or c == "_":
            out.append(c)
        else:
            out.append("_")
    s = "".join(out)
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_") or "x"


def _device_id_safe():
    return _sanitize_object_id(Config.settings.get("device_id") or "unknown")


def _topic_root():
    return f"luftdaten/{_device_id_safe()}"


def _availability_topic():
    return f"{_topic_root()}/availability"


def _state_topic(sensor_idx, dim):
    return f"{_topic_root()}/s{sensor_idx}_d{dim}/state"


def _discovery_object_id(sensor_idx, dim):
    return _sanitize_object_id(f"ld_{_device_id_safe()}_s{sensor_idx}_d{dim}")


def _unique_id(sensor_idx, dim):
    return f"ld_{Config.settings.get('device_id', '')}_{sensor_idx}_{dim}"


def _display_device_name():
    n = Config.settings.get("MQTT_DEVICE_NAME")
    if n and str(n).strip():
        return str(n).strip()
    if Config.settings.get("MODEL") == LdProduct.AIR_CUBE:
        return "Air Cube"
    if Config.settings.get("MODEL") == LdProduct.AIR_STATION:
        return "Air Station"
    return "Luftdaten"


def _firmware_version():
    return "{}.{}.{}".format(
        Config.settings.get("FIRMWARE_MAJOR") or 0,
        Config.settings.get("FIRMWARE_MINOR") or 0,
        Config.settings.get("FIRMWARE_PATCH") or 0,
    )


def _dimension_device_class(dim):
    m = {
        Dimension.PM0_1: "pm1",
        Dimension.PM1_0: "pm1",
        Dimension.PM2_5: "pm25",
        Dimension.PM4_0: None,
        Dimension.PM10_0: "pm10",
        Dimension.HUMIDITY: "humidity",
        Dimension.TEMPERATURE: "temperature",
        Dimension.PRESSURE: "pressure",
        Dimension.CO2: "carbon_dioxide",
        Dimension.TVOC: "volatile_organic_compounds_parts",
        Dimension.ADJUSTED_TEMP_CUBE: "temperature",
    }
    return m.get(int(dim))


def _dimension_unit(dim):
    return Dimension.get_unit(int(dim))


def _format_value(dim, val):
    try:
        v = float(val)
    except (TypeError, ValueError):
        return None
    s_test = "{:.4g}".format(v)
    if s_test.lower() in ("nan", "inf", "-inf"):
        return None
    d = int(dim)
    if d in (
        Dimension.TEMPERATURE,
        Dimension.ADJUSTED_TEMP_CUBE,
        Dimension.HUMIDITY,
        Dimension.PRESSURE,
    ):
        return "{:.2f}".format(v)
    if d in (
        Dimension.PM0_1,
        Dimension.PM1_0,
        Dimension.PM2_5,
        Dimension.PM4_0,
        Dimension.PM10_0,
        Dimension.CO2,
        Dimension.TVOC,
    ):
        return "{:.2f}".format(v)
    return "{:.4g}".format(v)


def _disconnect_silent():
    global _mqtt
    if _mqtt is None:
        return
    try:
        _mqtt.disconnect()
    except Exception:
        pass
    try:
        _mqtt.deinit()
    except Exception:
        pass
    _mqtt = None


def notify_settings_changed_from_ble():
    """Call after MQTT-related TLV writes so broker and discovery refresh."""
    global _discovery_dirty, _last_broker_key
    _discovery_dirty = True
    _last_broker_key = None
    _discovery_sent_keys.clear()
    _disconnect_silent()


def _broker_tuple():
    broker = str(Config.settings.get("MQTT_BROKER") or "").strip()
    use_tls = _coerce_bool(Config.settings.get("MQTT_USE_TLS"))
    port = Config.settings.get("MQTT_PORT")
    try:
        port = int(port)
    except (TypeError, ValueError):
        port = 8883 if use_tls else 1883
    user = str(Config.settings.get("MQTT_USERNAME") or "")
    pw = str(Config.settings.get("MQTT_PASSWORD") or "")
    cert = str(Config.settings.get("MQTT_CERTIFICATE_PATH") or "").strip()
    return (broker, port, use_tls, user, pw, cert)


def _ensure_mqtt_client():
    global _mqtt, _last_broker_key, _discovery_dirty, _discovery_sent_keys

    if not _model_supported():
        return False

    if not _coerce_bool(Config.settings.get("MQTT_ENABLED")):
        _disconnect_silent()
        return False

    if not WifiUtil.radio.connected or WifiUtil.pool is None:
        _disconnect_silent()
        return False

    bkey = _broker_tuple()
    broker = bkey[0]
    if not broker:
        _disconnect_silent()
        return False

    if bkey != _last_broker_key:
        _disconnect_silent()
        _discovery_sent_keys.clear()
        _last_broker_key = bkey

    if _mqtt is not None and _mqtt.is_connected():
        if _discovery_dirty:
            _discovery_sent_keys.clear()
        return True

    import adafruit_minimqtt.adafruit_minimqtt as MMQTT

    use_tls = bkey[2]
    port = bkey[1]
    user = bkey[3]
    pw = bkey[4]
    cert = bkey[5]

    ssl_ctx = None
    if use_tls:
        ssl_ctx = create_default_context()
        path = cert if cert else Config.runtime_settings.get("CERTIFICATE_PATH", "certs/isrgrootx1.pem")
        with open(path, "r") as f:
            ssl_ctx.load_verify_locations(cadata=f.read())

    cid = str(Config.settings.get("device_id") or "ld0")

    _mqtt = MMQTT.MQTT(
        broker=broker,
        port=port,
        username=user if user else None,
        password=pw if pw else None,
        client_id=cid,
        is_ssl=use_tls,
        keep_alive=60,
        recv_timeout=20,
        socket_pool=WifiUtil.pool,
        ssl_context=ssl_ctx,
        socket_timeout=2,
        connect_retries=3,
    )

    av = _availability_topic()
    _mqtt.will_set(topic=av, payload="offline", qos=0, retain=True)
    _mqtt.connect(host=broker, port=port)
    _mqtt.publish(av, "online", retain=True, qos=0)
    _discovery_dirty = True
    _discovery_sent_keys.clear()
    gc.collect()
    return True


def _publish_discovery(sensor_idx, dim):
    global _mqtt
    if _mqtt is None or not _mqtt.is_connected():
        return

    prefix = str(Config.settings.get("MQTT_DISCOVERY_PREFIX") or "homeassistant").strip().strip("/")
    oid = _discovery_object_id(sensor_idx, dim)
    topic = f"{prefix}/sensor/{oid}/config"

    dev = {
        "identifiers": ["luftdaten_{}".format(Config.settings.get("device_id", ""))],
        "name": _display_device_name(),
        "manufacturer": "Luftdaten.at",
        "model": str(Config.settings.get("MODEL")),
        "sw_version": _firmware_version(),
    }

    dim_i = int(dim)
    name = "{} S{} {}".format(_display_device_name(), sensor_idx, Dimension.get_name(dim_i))
    payload = {
        "name": name,
        "unique_id": _unique_id(sensor_idx, dim_i),
        "state_topic": _state_topic(sensor_idx, dim_i),
        "availability_topic": _availability_topic(),
        "payload_available": "online",
        "payload_not_available": "offline",
        "device": dev,
        "state_class": "measurement",
    }
    u = _dimension_unit(dim_i)
    if u and u != "Unknown":
        payload["unit_of_measurement"] = u
    dc = _dimension_device_class(dim_i)
    if dc:
        payload["device_class"] = dc

    try:
        _mqtt.publish(topic, json.dumps(payload), retain=True, qos=0)
    except Exception as e:
        logger.warning("MqttHa discovery publish failed: {}".format(e))
        raise
    gc.collect()


def publish_measurement_if_enabled(data):
    """Publish HA state (and discovery on first sighting) for one ``get_json()`` dict."""
    if not _model_supported():
        return
    if not _coerce_bool(Config.settings.get("MQTT_ENABLED")):
        return
    if not WifiUtil.radio.connected or WifiUtil.pool is None:
        return

    try:
        if not _ensure_mqtt_client():
            return
    except Exception as e:
        logger.warning("MqttHa connect failed: {}".format(e))
        _disconnect_silent()
        return

    sensors = data.get("sensors")
    if not isinstance(sensors, dict):
        return

    global _discovery_dirty
    if _discovery_dirty:
        _discovery_sent_keys.clear()
        _discovery_dirty = False

    for sid, sblock in sensors.items():
        if not isinstance(sblock, dict):
            continue
        body = sblock.get("data")
        if not isinstance(body, dict):
            continue
        try:
            sensor_idx = int(sid)
        except (TypeError, ValueError):
            continue
        for dim_key, val in body.items():
            try:
                dim = int(dim_key)
            except (TypeError, ValueError):
                continue
            payload = _format_value(dim, val)
            if payload is None:
                continue
            key = (sensor_idx, dim)
            try:
                if key not in _discovery_sent_keys:
                    _publish_discovery(sensor_idx, dim)
                    _discovery_sent_keys.add(key)
                if _mqtt is not None:
                    _mqtt.publish(_state_topic(sensor_idx, dim), payload, retain=False, qos=0)
            except Exception as e:
                logger.warning("MqttHa state publish failed: {}".format(e))
                _disconnect_silent()
                return
    gc.collect()


def loop_step():
    """Drive MiniMQTT ``loop()`` when MQTT is enabled (call every main iteration)."""
    if not _model_supported():
        return
    if not _coerce_bool(Config.settings.get("MQTT_ENABLED")):
        return
    if not WifiUtil.radio.connected or WifiUtil.pool is None:
        _disconnect_silent()
        return
    if _mqtt is None or not _mqtt.is_connected():
        try:
            _ensure_mqtt_client()
        except Exception:
            _disconnect_silent()
        return
    try:
        _mqtt.loop(timeout=0)
    except Exception as e:
        logger.debug("MqttHa loop: {}".format(e))
        _disconnect_silent()
