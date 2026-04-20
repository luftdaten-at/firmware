"""One-shot actions driven by /startup.toml flags (see startup.toml)."""
import errno
import json
import os

import gc
import storage
from lib.cptoml import fetch, put
from storage import remount

from config import Config
from logger import logger
from tz_format import format_iso8601_tz
from wifi_client import WifiUtil

STARTUP_TOML = "/startup.toml"
DATAHUB_UPLOAD_LOG_PATH = "/datahub_upload.log"


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


def _append_datahub_upload_log(msg: str) -> None:
    """Append one line to ``DATAHUB_UPLOAD_LOG_PATH`` on CIRCUITPY root; never raises."""
    rw = False
    try:
        try:
            storage.remount(
                "/",
                readonly=False,
                disable_concurrent_write_protection=True,
            )
        except TypeError:
            remount("/", False)
        rw = True
        with open(DATAHUB_UPLOAD_LOG_PATH, "a") as f:
            f.write(msg + "\n")
            f.flush()
    except Exception:
        pass
    finally:
        if rw:
            try:
                storage.remount("/", True)
            except TypeError:
                remount("/", True)
            except Exception:
                pass


def _datahub_upload_timestamp() -> str:
    return format_iso8601_tz()


def _datahub_response_body_snippet(resp, max_len: int = 480) -> str:
    try:
        t = resp.text
    except Exception:
        return "(no body)"
    if not t:
        return "(empty)"
    t = t.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    if len(t) > max_len:
        return t[:max_len] + "…"
    return t


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


def _run_upload_sd_log_to_datahub() -> None:
    """POST wifiless SD JSONL log to station data/ API; see startup.toml UPLOAD_SD_LOG_TO_DATAHUB."""
    if not _truthy(fetch_startup_flag("UPLOAD_SD_LOG_TO_DATAHUB")):
        return
    if not Config.is_air_station_wifiless():
        logger.warning(
            "startup.toml: UPLOAD_SD_LOG_TO_DATAHUB is set but device is not Air Station wifiless; skipping"
        )
        return
    if not Config.settings.get("SSID"):
        logger.warning(
            "startup.toml: UPLOAD_SD_LOG_TO_DATAHUB requires SSID in settings.toml; skipping"
        )
        return

    from sd_logger import ensure_sd_mounted

    log_path = Config.settings.get("SD_LOG_PATH") or "/sd/measurements.jsonl"
    logger.info(f"startup.toml: UPLOAD_SD_LOG_TO_DATAHUB — uploading {log_path}")

    if not WifiUtil.connect():
        logger.warning(
            "startup.toml: WiFi connect failed; UPLOAD_SD_LOG_TO_DATAHUB left true for a later boot"
        )
        return

    if not ensure_sd_mounted():
        logger.warning(
            "startup.toml: SD card not available; UPLOAD_SD_LOG_TO_DATAHUB left true for a later boot"
        )
        return

    try:
        try:
            with open(log_path, "r") as f:
                has_nonempty_line = False
                for line in f:
                    if line.strip():
                        has_nonempty_line = True
                        break
        except OSError as e:
            eno = getattr(e, "errno", None)
            if eno == errno.ENOENT or eno == 2 or "No such file" in str(e):
                logger.info(
                    "startup.toml: SD log file missing; clearing UPLOAD_SD_LOG_TO_DATAHUB"
                )
                clear_startup_flag("UPLOAD_SD_LOG_TO_DATAHUB")
                return
            raise

        if not has_nonempty_line:
            logger.info("startup.toml: SD log missing or empty; clearing UPLOAD_SD_LOG_TO_DATAHUB")
            clear_startup_flag("UPLOAD_SD_LOG_TO_DATAHUB")
            return

        with open(log_path, "r") as f:
            for line_no, line in enumerate(f, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                except ValueError as e:
                    logger.error(f"SD log line {line_no}: invalid JSON ({e}); aborting upload")
                    return
                gc.collect()
                try:
                    resp = WifiUtil.send_json_to_api(payload)
                except Exception as e:
                    logger.error(f"SD log line {line_no}: request failed ({e}); aborting upload")
                    _append_datahub_upload_log(
                        f"{_datahub_upload_timestamp()} line={line_no} http=error "
                        f"{type(e).__name__}: {e}"
                    )
                    return
                _append_datahub_upload_log(
                    f"{_datahub_upload_timestamp()} line={line_no} http={resp.status_code} "
                    f"body={_datahub_response_body_snippet(resp)}"
                )
                if resp.status_code not in (200, 422):
                    logger.error(
                        f"SD log line {line_no}: HTTP {resp.status_code}; aborting upload, log file unchanged"
                    )
                    return

        with open(log_path, "w") as wf:
            wf.write("")
        if hasattr(os, "sync"):
            os.sync()
        logger.info("startup.toml: SD log uploaded; file truncated; clearing UPLOAD_SD_LOG_TO_DATAHUB")
        clear_startup_flag("UPLOAD_SD_LOG_TO_DATAHUB")
    except Exception as e:
        logger.error(f"startup.toml: UPLOAD_SD_LOG_TO_DATAHUB failed: {e}")


def _run_clear_sd_card() -> None:
    """Remove all content under ``/sd``; see startup.toml CLEAR_SD_CARD."""
    if not _truthy(fetch_startup_flag("CLEAR_SD_CARD")):
        return
    if not Config.is_air_station_wifiless():
        logger.warning(
            "startup.toml: CLEAR_SD_CARD is set but device is not Air Station wifiless; skipping"
        )
        return
    from sd_logger import clear_sd_volume

    logger.info("startup.toml: CLEAR_SD_CARD — deleting all files under /sd")
    if not clear_sd_volume():
        logger.warning(
            "startup.toml: CLEAR_SD_CARD failed; flag left true for a later boot"
        )
        return
    clear_startup_flag("CLEAR_SD_CARD")


def run_startup_actions_after_sensors(connected_sensors, battery_monitor) -> None:
    """Run after I2C sensor scan; model detection needs ``connected_sensors`` / battery monitor."""
    try:
        _run_detect_model_from_sensors(connected_sensors, battery_monitor)
    except Exception as e:
        logger.error(f"startup_actions_after_sensors: unexpected error: {e}")
    try:
        _run_upload_sd_log_to_datahub()
    except Exception as e:
        logger.error(f"startup_actions_after_sensors (SD upload): unexpected error: {e}")
    try:
        _run_clear_sd_card()
    except Exception as e:
        logger.error(f"startup_actions_after_sensors (CLEAR_SD_CARD): unexpected error: {e}")
