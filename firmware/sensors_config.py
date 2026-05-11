"""
``sensors.toml`` — which `SensorModel` ids to probe at boot. See ``docs/settings.md``.
"""
import errno
import os

import storage
from storage import remount

from enums import SensorModel
from lib.cptoml import fetch
from logger import logger
from sensors_toml_ids import parse_comma_separated_ints
from util import get_connected_sensors

SENSORS_TOML = "/sensors.toml"
SENSORS_TOML_KEY = "SENSOR_MODEL_IDS"
PS1_MODEL_ID = SensorModel.PS1_NO2_50_MOD


def parse_model_ids_string(raw):
    """
    Comma-separated integers from TOML. Empty/whitespace -> [].
    Invalid tokens are logged and skipped.
    """
    out, bad = parse_comma_separated_ints(raw)
    for part in bad:
        logger.warning(
            f"sensors.toml: ignore non-integer in SENSOR_MODEL_IDS: {part!r}"
        )
    return out


def sensors_toml_exists() -> bool:
    try:
        os.stat(SENSORS_TOML)
        return True
    except OSError as e:
        if e.errno == errno.ENOENT:
            return False
        raise


def read_sensors_toml():
    """
    Return list of model ids, or None if file missing, unreadable, or empty/invalid
    (so a full rediscover is triggered).
    """
    if not sensors_toml_exists():
        return None
    try:
        s = fetch(SENSORS_TOML_KEY, toml=SENSORS_TOML)
    except OSError:
        return None
    if s is None:
        return None
    ids = parse_model_ids_string(s)
    if not ids:
        logger.warning("sensors.toml: SENSOR_MODEL_IDS empty; running full sensor scan")
        return None
    return ids


def write_sensors_toml(model_ids) -> None:
    """Create or replace ``sensors.toml`` with comma-separated `SensorModel` ids."""
    from tz_format import format_iso8601_tz

    unique_sorted = sorted(set(int(m) for m in model_ids))
    body = ", ".join(str(x) for x in unique_sorted)
    t = format_iso8601_tz()
    text = (
        f"# Probed SensorModel ids (integers). Updated at {t}\n"
        f'{SENSORS_TOML_KEY} = "{body}"\n'
    )
    try:
        try:
            storage.remount(
                "/",
                readonly=False,
                disable_concurrent_write_protection=True,
            )
        except TypeError:
            remount("/", False)
    except OSError:
        pass
    with open(SENSORS_TOML, "w") as f:
        f.write(text)
    try:
        try:
            storage.remount(
                "/",
                readonly=True,
            )
        except TypeError:
            remount("/", True)
    except OSError:
        pass
    logger.info(f"sensors.toml: wrote {SENSORS_TOML_KEY} ({body!r})")


def _try_ps1(connected_sensors) -> bool:
    """
    If PS1 connects, add it to ``connected_sensors`` (in place). Returns whether found.
    """
    try:
        from sensors.sensor_ps1_no2 import Ps1No2Sensor

        ps1 = Ps1No2Sensor()
        if ps1.attempt_connection():
            connected_sensors[ps1.model_id] = ps1
            logger.info("Found sensor: PS1-NO2-50-MOD")
            return True
    except Exception as e:
        logger.warning(f"PS1-NO2-50-MOD UART initialization failed: {e}")
    return False


def attach_ps1_if_in_model_ids(model_ids, connected_sensors) -> None:
    """Probe UART NO2 if PS1 is included in the configured id list."""
    if model_ids and PS1_MODEL_ID in model_ids:
        _try_ps1(connected_sensors)


def full_i2c_and_ps1_discovery(i2c):
    """
    Probe all supported I2C types, then PS1. Returns ``connected_sensors`` dict
    of devices that responded.
    """
    connected = get_connected_sensors(i2c, model_ids=None)
    attach_ps1_if_in_model_ids((PS1_MODEL_ID,), connected)
    return connected


def resolve_connected_sensors(i2c):
    """
    Probes sensors according to ``sensors.toml`` or after a full discover when
    the file is missing, ``REFRESH_SENSORS_TOML`` in ``/startup.toml`` is set, or
    the file is invalid. Writes ``sensors.toml`` on full discover. Clears the
    refresh flag after a successful full pass.
    """
    from startup_actions import clear_startup_flag, fetch_startup_flag

    def _truthy(value) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes")
        return bool(value)

    missing = not sensors_toml_exists()
    try:
        refresh = _truthy(fetch_startup_flag("REFRESH_SENSORS_TOML"))
    except OSError:
        refresh = False

    if missing or refresh:
        logger.info(
            "sensors: full I2C + PS1 discover (no sensors.toml, REFRESH, or invalid file)"
        )
        connected = full_i2c_and_ps1_discovery(i2c)
        # Do not create an empty file on first install with no sensors; always persist
        # when refreshing so a removed or updated layout is reflected in sensors.toml.
        if connected or (refresh and not missing):
            write_sensors_toml(connected.keys())
        if refresh:
            try:
                clear_startup_flag("REFRESH_SENSORS_TOML")
            except OSError as e:
                logger.error(f"Could not clear REFRESH_SENSORS_TOML: {e}")
        return connected

    ids = read_sensors_toml()
    if ids is None:
        connected = full_i2c_and_ps1_discovery(i2c)
        if connected:
            write_sensors_toml(connected.keys())
        return connected

    connected = get_connected_sensors(i2c, model_ids=ids)
    attach_ps1_if_in_model_ids(ids, connected)
    return connected
