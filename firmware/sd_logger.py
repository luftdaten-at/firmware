"""SPI SD card mount and JSONL append for Air Station wifiless mode.

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
