"""SPI SD card mount and JSONL append for Air Station / Air Cube.

Used for wifiless mode and for Air Station Wi‑Fi mode offline buffering.

Hardware: SCK=IO12, MISO=IO11, MOSI=IO10, CS=IO13 (ESP32-S3 / board.IO*).
"""
import json
import os

import adafruit_sdcard  # type: ignore
import board  # type: ignore
import busio  # type: ignore
import digitalio  # type: ignore
import storage  # type: ignore

from config import Config
from logger import logger

_mounted = False
_spi = None
_cs_pin = None
_sdcard = None


def _reset_mount_state():
    global _mounted, _spi, _cs_pin, _sdcard
    _mounted = False
    _spi = None
    _cs_pin = None
    _sdcard = None


def _sd_join(root: str, name: str) -> str:
    r = root.rstrip("/")
    return f"{r}/{name}"


def _delete_sd_path(full: str) -> None:
    """Remove a file or recursively remove a directory under ``/sd``."""
    try:
        entries = os.listdir(full)
    except OSError:
        os.remove(full)
        return
    for n in entries:
        if n in (".", ".."):
            continue
        _delete_sd_path(_sd_join(full, n))
    try:
        os.rmdir(full)
    except OSError:
        pass


def clear_sd_volume() -> bool:
    """Delete all files and directories under ``/sd`` (not the mount itself).

    Mounts the card if needed. Returns ``True`` if every entry was removed without error.
    """
    if not ensure_sd_mounted():
        return False
    try:
        for name in os.listdir("/sd"):
            if name in (".", ".."):
                continue
            _delete_sd_path(_sd_join("/sd", name))
        if hasattr(os, "sync"):
            os.sync()
        logger.info("SD card: all entries under /sd removed")
        return True
    except Exception as e:
        logger.error(f"SD card clear failed ({type(e).__name__}: {e})")
        return False


def ensure_sd_mounted():
    """Mount FAT volume at /sd once per boot. Returns True if ready to write."""
    global _mounted, _spi, _cs_pin, _sdcard
    if _mounted:
        return True
    try:
        _spi = busio.SPI(board.IO12, board.IO10, board.IO11)
        _cs_pin = digitalio.DigitalInOut(board.IO13)
        _sdcard = adafruit_sdcard.SDCard(_spi, _cs_pin)
        vfs = storage.VfsFat(_sdcard)
        storage.mount(vfs, '/sd')
        _mounted = True
        logger.info('SD card mounted at /sd')
        return True
    except Exception as e:
        logger.warning(f'SD card mount failed ({type(e).__name__}: {e})')
        try:
            storage.umount('/sd')
        except Exception:
            pass
        for obj in (_cs_pin, _spi):
            if obj is not None:
                try:
                    obj.deinit()
                except Exception:
                    pass
        _reset_mount_state()
        return False


def append_measurement_jsonl(payload: dict) -> bool:
    """Append one JSON object per line (same shape as API payload)."""
    path = Config.settings.get('SD_LOG_PATH') or '/sd/measurements.jsonl'
    if not ensure_sd_mounted():
        return False
    try:
        line = json.dumps(payload) + '\n'
        with open(path, 'a') as f:
            f.write(line)
            f.flush()
        return True
    except Exception as e:
        logger.error(f'SD log write failed ({type(e).__name__}: {e})')
        try:
            storage.umount('/sd')
        except Exception:
            pass
        _reset_mount_state()
        return False


def _write_jsonl_lines(path: str, lines) -> None:
    with open(path, 'w') as f:
        for ln in lines:
            f.write(ln if ln.endswith('\n') else ln + '\n')
    if hasattr(os, 'sync'):
        os.sync()


def replay_pending_jsonl_to_api() -> bool:
    """POST buffered JSONL lines via ``send_json_to_api``; remove accepted lines (HTTP 200/422).

    Returns ``True`` when the log file has no remaining non-empty lines.
    """
    from wifi_client import WifiUtil

    if not WifiUtil.radio.connected:
        return False

    path = Config.settings.get('SD_LOG_PATH') or '/sd/measurements.jsonl'
    if not ensure_sd_mounted():
        return False

    try:
        with open(path, 'r') as f:
            pending = f.readlines()
    except OSError as e:
        eno = getattr(e, 'errno', None)
        if eno == 2 or 'No such file' in str(e):
            return True
        logger.error(f'SD log read failed ({type(e).__name__}: {e})')
        return False

    if not any(ln.strip() for ln in pending):
        return True

    idx = 0
    sent = 0
    while idx < len(pending):
        stripped = pending[idx].strip()
        if not stripped:
            idx += 1
            continue
        line_no = idx + 1
        try:
            payload = json.loads(stripped)
        except ValueError as e:
            logger.error(f'SD log line {line_no}: invalid JSON ({e}); keeping from this line onward')
            break
        try:
            resp = WifiUtil.send_json_to_api(payload)
        except Exception as e:
            logger.warning(
                f'SD log line {line_no}: upload failed ({type(e).__name__}: {e}); keeping from this line onward'
            )
            break
        if resp.status_code not in (200, 422):
            logger.warning(
                f'SD log line {line_no}: HTTP {resp.status_code}; keeping from this line onward'
            )
            break
        idx += 1
        sent += 1

    unsent = pending[idx:]
    try:
        _write_jsonl_lines(path, unsent)
    except Exception as e:
        logger.error(f'SD log rewrite failed ({type(e).__name__}: {e})')
        return False

    if sent:
        logger.info(f'SD log: uploaded {sent} buffered measurement(s)')
    return not any(ln.strip() for ln in unsent)


def wifiless_button_upload_sd_backlog() -> str:
    """Connect Wi-Fi (if ``SSID`` set) and POST buffered SD JSONL measurements.

    Returns ``ok``, ``no_ssid``, ``connect_failed``, or ``partial`` (some lines remain).
    """
    from wifi_client import WifiUtil

    if not Config.settings.get("SSID"):
        logger.info("Wifiless button upload: no SSID configured")
        return "no_ssid"

    logger.info("Wifiless button upload: connecting Wi-Fi")
    if not WifiUtil.connect():
        logger.warning("Wifiless button upload: Wi-Fi connect failed")
        return "connect_failed"

    if not Config.runtime_settings.get("rtc_is_set"):
        try:
            WifiUtil.set_RTC()
        except Exception as e:
            logger.warning(f"Wifiless button upload: NTP/RTC sync skipped ({type(e).__name__}: {e})")

    if replay_pending_jsonl_to_api():
        return "ok"
    return "partial"
