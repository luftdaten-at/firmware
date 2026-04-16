"""One-shot actions driven by /startup.toml flags (see startup.toml)."""
from lib.cptoml import fetch, put
from storage import remount

from config import Config
from logger import logger
from wifi_client import WifiUtil

STARTUP_TOML = "/startup.toml"


def _truthy(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes")
    return bool(value)


def fetch_startup_flag(key: str):
    """Return value from startup.toml or None if missing/unreadable."""
    try:
        return fetch(key, toml=STARTUP_TOML)
    except OSError:
        return None


def clear_startup_flag(key: str) -> None:
    try:
        remount("/", False)
        put(key, False, toml=STARTUP_TOML)
        remount("/", True)
    except OSError as e:
        logger.error(f"Could not clear {STARTUP_TOML} flag {key!r}: {e}")


def _run_sync_rtc_from_ntp() -> None:
    val = fetch_startup_flag("SYNC_RTC_FROM_NTP")
    if val is None or not _truthy(val):
        return
    if not Config.settings.get("SSID"):
        logger.warning(
            "startup.toml: SYNC_RTC_FROM_NTP is true but SSID is empty; "
            "set Wi-Fi in settings.toml and reboot."
        )
        return
    logger.info("startup.toml: SYNC_RTC_FROM_NTP — connecting for NTP time sync")
    if WifiUtil.connect():
        logger.info("startup.toml: WiFi/NTP sync succeeded; clearing SYNC_RTC_FROM_NTP")
        clear_startup_flag("SYNC_RTC_FROM_NTP")
    else:
        logger.warning(
            "startup.toml: WiFi connect failed; SYNC_RTC_FROM_NTP left true for a later boot"
        )


def run_startup_actions() -> None:
    """Run after I2C / DS3231 probe so rtc_module exists for NTP → DS3231 write."""
    try:
        _run_sync_rtc_from_ntp()
    except Exception as e:
        logger.error(f"startup_actions: unexpected error: {e}")


def _run_detect_model_from_sensors(connected_sensors, battery_monitor) -> None:
    """Set MODEL from sensors when startup flag or legacy MODEL == -1 (see startup.toml)."""
    from util import get_model_id_from_sensors

    flag_detect = _truthy(fetch_startup_flag("DETECT_MODEL_FROM_SENSORS"))
    legacy_minus_one = Config.settings.get("MODEL") == -1
    if not flag_detect and not legacy_minus_one:
        return
    reason = (
        "startup.toml DETECT_MODEL_FROM_SENSORS"
        if flag_detect
        else "settings.toml MODEL == -1"
    )
    logger.info(f"Model auto-detect ({reason})")
    m = get_model_id_from_sensors(connected_sensors, battery_monitor)
    Config.settings["MODEL"] = m
    Config.set_api_url()
    if flag_detect:
        clear_startup_flag("DETECT_MODEL_FROM_SENSORS")


def run_startup_actions_after_sensors(connected_sensors, battery_monitor) -> None:
    """Run after I2C sensor scan; model detection needs ``connected_sensors`` / battery monitor."""
    try:
        _run_detect_model_from_sensors(connected_sensors, battery_monitor)
    except Exception as e:
        logger.error(f"startup_actions_after_sensors: unexpected error: {e}")
